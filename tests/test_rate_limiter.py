"""Tests for the shared token-bucket + AIMD rate limiter.

The limiter is a pure async unit with no HTTP. To keep tests deterministic it
accepts an injected monotonic clock and (async) sleep function, so "time"
advances explicitly and nothing actually blocks.
"""

import asyncio
import time

from letras.source.rate_limiter import RateLimiter


class FakeClock:
    """A controllable monotonic clock; ``sleep`` advances it instantly so the
    async tests progress virtual time without ever blocking. Single-threaded
    asyncio means no lock is needed."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds


def _limiter(clock: FakeClock, **kw: float) -> RateLimiter:
    params: dict[str, float] = {
        "rate": 10.0,
        "burst": 1.0,
        "min_rate": 1.0,
        "max_rate": 40.0,
        "jitter": 0.0,
    }
    params.update(kw)
    return RateLimiter(
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        **params,  # type: ignore[arg-type]
    )


async def test_first_acquire_is_immediate() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, burst=1.0)

    await limiter.acquire()

    assert clock.now == 0.0  # one burst token available at start


async def test_acquire_blocks_until_a_token_refills() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0, burst=1.0)  # 1 token / 0.1s

    await limiter.acquire()  # consumes the initial token
    await limiter.acquire()  # must wait 0.1s for the next

    assert clock.now == 0.1


async def test_rate_decreases_multiplicatively_on_backoff() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=20.0, backoff_factor=0.5)

    await limiter.on_throttled(retry_after=None)

    assert limiter.rate == 10.0  # halved


async def test_backoff_respects_min_rate_floor() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=2.0, min_rate=1.0, backoff_factor=0.5)

    await limiter.on_throttled(retry_after=None)
    await limiter.on_throttled(retry_after=None)

    assert limiter.rate == 1.0  # clamped to the floor, not 0.5


async def test_success_increases_rate_additively_toward_ceiling() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0, max_rate=12.0, increase_step=1.0)

    limiter.on_success()
    assert limiter.rate == 11.0
    limiter.on_success()
    assert limiter.rate == 12.0
    limiter.on_success()
    assert limiter.rate == 12.0  # never exceeds the ceiling


async def test_throttle_with_retry_after_sleeps_for_that_duration() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0)

    await limiter.on_throttled(retry_after=3.0)

    assert clock.now == 3.0  # honored the server's Retry-After


async def test_throttle_without_retry_after_does_not_sleep() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0)

    await limiter.on_throttled(retry_after=None)

    assert clock.now == 0.0  # backoff is via the rate, not a forced sleep


async def test_acquire_is_concurrency_safe_and_does_not_over_issue() -> None:
    # Concurrency invariant on a real (short) wall clock: with a high rate and
    # generous burst, many coroutines each acquiring once must all complete and
    # the bucket must never hand out more than it should for the elapsed time.
    # Real time + bounded work => fast and cannot livelock.
    limiter = RateLimiter(rate=1000.0, burst=20.0, jitter=0.0)
    n = 40

    start = time.monotonic()
    await asyncio.gather(*(limiter.acquire() for _ in range(n)))
    elapsed = time.monotonic() - start

    # n tokens cost at least (n - burst) / rate seconds of refill (the burst is
    # free); the limiter must not have issued them faster than the rate allows.
    assert elapsed >= (n - 20) / 1000.0 - 1e-3
