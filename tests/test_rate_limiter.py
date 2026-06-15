"""Tests for the shared token-bucket + AIMD rate limiter.

The limiter is a pure, thread-safe unit with no HTTP. To keep tests
deterministic it accepts an injected monotonic clock and sleep function, so
"time" advances explicitly and nothing actually blocks.
"""

import threading
import time

from letras.source.rate_limiter import RateLimiter


class FakeClock:
    """A controllable, thread-safe monotonic clock; ``sleep`` advances it
    instantly (read-modify-write is locked so the concurrency test is
    deterministic)."""

    def __init__(self) -> None:
        self.now = 0.0
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self.now

    def sleep(self, seconds: float) -> None:
        # Sleeping advances virtual time without blocking the test.
        with self._lock:
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


def test_first_acquire_is_immediate() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, burst=1.0)

    limiter.acquire()

    assert clock.now == 0.0  # one burst token available at start


def test_acquire_blocks_until_a_token_refills() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0, burst=1.0)  # 1 token / 0.1s

    limiter.acquire()  # consumes the initial token
    limiter.acquire()  # must wait 0.1s for the next

    assert clock.now == 0.1


def test_rate_decreases_multiplicatively_on_backoff() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=20.0, backoff_factor=0.5)

    limiter.on_throttled(retry_after=None)

    assert limiter.rate == 10.0  # halved


def test_backoff_respects_min_rate_floor() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=2.0, min_rate=1.0, backoff_factor=0.5)

    limiter.on_throttled(retry_after=None)
    limiter.on_throttled(retry_after=None)

    assert limiter.rate == 1.0  # clamped to the floor, not 0.5


def test_success_increases_rate_additively_toward_ceiling() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0, max_rate=12.0, increase_step=1.0)

    limiter.on_success()
    assert limiter.rate == 11.0
    limiter.on_success()
    assert limiter.rate == 12.0
    limiter.on_success()
    assert limiter.rate == 12.0  # never exceeds the ceiling


def test_throttle_with_retry_after_sleeps_for_that_duration() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0)

    limiter.on_throttled(retry_after=3.0)

    assert clock.now == 3.0  # honored the server's Retry-After


def test_throttle_without_retry_after_does_not_sleep() -> None:
    clock = FakeClock()
    limiter = _limiter(clock, rate=10.0)

    limiter.on_throttled(retry_after=None)

    assert clock.now == 0.0  # backoff is via the rate, not a forced sleep


def test_acquire_is_threadsafe_and_does_not_over_issue() -> None:
    # Concurrency invariant on a real (short) wall clock: with a high rate and
    # generous burst, many threads each acquiring once must all complete and
    # the bucket must never hand out more than it should for the elapsed time.
    # Real time + bounded work => fast and cannot livelock.
    limiter = RateLimiter(rate=1000.0, burst=20.0, jitter=0.0)
    n = 40
    counter = {"done": 0}
    lock = threading.Lock()

    def worker() -> None:
        limiter.acquire()
        with lock:
            counter["done"] += 1

    start = time.monotonic()
    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    elapsed = time.monotonic() - start

    assert counter["done"] == n  # every thread got through; no deadlock
    # n tokens cost at least (n - burst) / rate seconds of refill (the burst is
    # free); the limiter must not have issued them faster than the rate allows.
    assert elapsed >= (n - 20) / 1000.0 - 1e-3
