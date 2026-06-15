"""A shared, thread-safe request-rate governor: token bucket + AIMD.

The pipeline runs many worker threads against one ``Fetcher``. A precise
global ceiling on requests/second is far gentler on the source than a crude
per-request ``time.sleep`` (which scales with worker count and bursts on
keepalive). This limiter is that ceiling, and it *adapts*: it backs off
multiplicatively when the server pushes back (``429``/``503``, honoring
``Retry-After``) and recovers additively on sustained success (AIMD). The net
effect is it automatically settles at the fastest rate the site tolerates,
so the site never *needs* to ban us.

Pure and testable: the monotonic clock and ``sleep`` are injected, so tests
advance virtual time without blocking and never touch the network.
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable


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
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
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
        self._lock = threading.Lock()

    @property
    def rate(self) -> float:
        with self._lock:
            return self._rate

    def acquire(self) -> None:
        """Block (cooperatively) until one request may proceed.

        Refills tokens for the elapsed time at the current rate, then either
        consumes a token or sleeps for exactly the shortfall. Optional jitter
        adds a small random pause so a burst of threads does not fire in
        lockstep. The loop re-checks after sleeping because ``rate`` may have
        changed (a concurrent backoff) while waiting.
        """
        while True:
            with self._lock:
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
                self._sleep(wait)
                continue
            if self._jitter > 0.0:
                self._sleep(self._rng.uniform(0.0, self._jitter))
            return

    def on_success(self) -> None:
        """Additive increase: nudge the rate up toward the ceiling."""
        with self._lock:
            self._rate = min(self._max_rate, self._rate + self._increase_step)

    def on_throttled(self, retry_after: float | None) -> None:
        """Multiplicative decrease, honoring an explicit ``Retry-After``.

        Halves (by ``backoff_factor``) the sustained rate down to ``min_rate``
        and, if the server told us how long to wait, sleeps that long so the
        very next attempt does not immediately re-trip the throttle.
        """
        with self._lock:
            self._rate = max(self._min_rate, self._rate * self._backoff_factor)
        if retry_after is not None and retry_after > 0.0:
            self._sleep(retry_after)
