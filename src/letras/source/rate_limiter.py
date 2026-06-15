"""A shared request-rate governor: token bucket + AIMD.

The pipeline runs one event loop driving many concurrent requests through one
``Fetcher``. A precise global ceiling on requests/second is far gentler on the
source than a crude per-request ``sleep`` (which scales with concurrency and
bursts on keepalive). This limiter is that ceiling, and it *adapts*: it backs
off multiplicatively when the server pushes back (``429``/``503``, honoring
``Retry-After``) and recovers additively on sustained success (AIMD). The net
effect is it automatically settles at the fastest rate the site tolerates, so
the site never *needs* to ban us.

Async and single-threaded: the limiter lives entirely on the event loop, so the
token read-modify-write needs no lock (it never ``await``s mid-update, so
coroutines can't interleave inside it). The monotonic clock and ``sleep`` are
injected, so tests advance virtual time without blocking and never touch the
network.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from time import monotonic as _monotonic


async def _sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class RateLimiter:
    def __init__(
        self,
        *,
        rate: float,
        burst: float = 1.0,
        min_rate: float = 0.5,
        max_rate: float = 40.0,
        increase_step: float = 0.5,
        backoff_factor: float = 0.5,
        jitter: float = 0.0,
        monotonic: Callable[[], float] = _monotonic,
        sleep: Callable[[float], Awaitable[None]] = _sleep,
        rng: random.Random | None = None,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._rate = max(min_rate, min(rate, max_rate))
        self._burst = max(burst, 1.0)
        self._tokens = self._burst
        self._increase_step = increase_step
        self._backoff_factor = backoff_factor
        self._jitter = jitter
        self._monotonic = monotonic
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._updated = monotonic()

    @property
    def rate(self) -> float:
        return self._rate

    async def acquire(self) -> None:
        """Block (cooperatively) until one request may proceed.

        Refills tokens for the elapsed time at the current rate, then either
        consumes a token or sleeps for exactly the shortfall. Optional jitter
        adds a small random pause so a burst of coroutines does not fire in
        lockstep. The loop re-checks after sleeping because ``rate`` may have
        changed (a concurrent backoff) while waiting.
        """
        while True:
            now = self._monotonic()
            elapsed = now - self._updated
            self._updated = now
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                wait = 0.0
            else:
                wait = (1.0 - self._tokens) / self._rate
            if wait > 0.0:
                await self._sleep(wait)
                continue
            if self._jitter > 0.0:
                await self._sleep(self._rng.uniform(0.0, self._jitter))
            return

    def on_success(self) -> None:
        """Additive increase: nudge the rate up toward the ceiling."""
        self._rate = min(self._max_rate, self._rate + self._increase_step)

    async def on_throttled(self, retry_after: float | None) -> None:
        """Multiplicative decrease, honoring an explicit ``Retry-After``.

        Halves (by ``backoff_factor``) the sustained rate down to ``min_rate``
        and, if the server told us how long to wait, sleeps that long so the
        very next attempt does not immediately re-trip the throttle.
        """
        self._rate = max(self._min_rate, self._rate * self._backoff_factor)
        if retry_after is not None and retry_after > 0.0:
            await self._sleep(retry_after)
