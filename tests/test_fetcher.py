import httpx
import pytest

from letras.source.fetcher import Fetcher, _parse_retry_after
from letras.source.rate_limiter import RateLimiter


async def test_fetcher_builds_paths_and_returns_body() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, text=f"BODY {request.url.path}")

    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)

    assert (
        await fetcher.song_page("aline-barros", "44039") == "BODY /aline-barros/44039/"
    )
    assert (
        await fetcher.artist_index()
        == "BODY /estilos/gospelreligioso/todosartistas.html"
    )
    assert "/aline-barros/44039/" in seen


async def test_fetcher_retries_transient_errors() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="OK")

    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)

    assert await fetcher.artist_index() == "OK"
    assert calls["n"] == 2  # one failure, one retry


def test_parse_retry_after() -> None:
    assert _parse_retry_after("3") == 3.0
    assert _parse_retry_after("0") == 0.0
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("-1") is None
    assert _parse_retry_after("Wed, 21 Oct 2025 07:28:00 GMT") is None  # date form


class _RecordingLimiter:
    """A stand-in for RateLimiter that records the control signals it gets."""

    def __init__(self) -> None:
        self.acquired = 0
        self.successes = 0
        self.throttles: list[float | None] = []

    async def acquire(self) -> None:
        self.acquired += 1

    def on_success(self) -> None:
        self.successes += 1

    async def on_throttled(self, retry_after: float | None) -> None:
        self.throttles.append(retry_after)


async def test_fetcher_acquires_a_token_and_signals_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    limiter = _RecordingLimiter()
    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client, rate_limiter=limiter)  # type: ignore[arg-type]

    assert await fetcher.artist_index() == "OK"
    assert limiter.acquired == 1
    assert limiter.successes == 1
    assert limiter.throttles == []


async def test_fetcher_backs_off_on_429_with_retry_after() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, text="OK")

    limiter = _RecordingLimiter()
    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client, rate_limiter=limiter)  # type: ignore[arg-type]

    assert await fetcher.artist_index() == "OK"  # retried after backing off
    assert calls["n"] == 2
    assert limiter.throttles == [2.0]  # honored Retry-After
    assert limiter.acquired == 2  # a token per attempt
    assert limiter.successes == 1  # success only on the second attempt


async def test_fetcher_backs_off_on_503_without_retry_after() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)  # no Retry-After header
        return httpx.Response(200, text="OK")

    limiter = _RecordingLimiter()
    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client, rate_limiter=limiter)  # type: ignore[arg-type]

    assert await fetcher.artist_index() == "OK"
    assert limiter.throttles == [None]  # backoff via rate, no forced sleep


async def test_fetcher_real_limiter_backoff_reduces_rate() -> None:
    # End-to-end with a real RateLimiter (injected no-op clock so nothing
    # blocks): a 429 must drop the sustained rate.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, text="OK")

    now = {"t": 0.0}

    async def fake_sleep(seconds: float) -> None:
        now["t"] += seconds

    limiter = RateLimiter(
        rate=20.0,
        burst=10.0,
        backoff_factor=0.5,
        increase_step=0.0,  # isolate the backoff: no success-ramp confounder
        monotonic=lambda: now["t"],
        sleep=fake_sleep,
    )
    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client, rate_limiter=limiter)

    assert await fetcher.artist_index() == "OK"
    assert limiter.rate == 10.0  # halved by the 429, no ramp
    assert now["t"] == 1.0  # slept for Retry-After


async def test_fetcher_default_client_negotiates_compression() -> None:
    # A default-constructed Fetcher builds its client to advertise br/gzip so
    # the source can compress (verified live: ~5-10x byte reduction).
    fetcher = Fetcher("https://letras.test")
    try:
        accept_encoding = fetcher._client.headers["accept-encoding"]
        assert "br" in accept_encoding
        assert "gzip" in accept_encoding
    finally:
        await fetcher.aclose()


async def test_fetcher_request_carries_compression_header() -> None:
    # And the negotiated header actually rides each outgoing request. We build
    # the client with the same headers the Fetcher uses plus a mock transport.
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(200, text="OK")

    client = httpx.AsyncClient(
        base_url="https://letras.test",
        headers={"Accept-Encoding": "gzip, deflate, br"},
        transport=httpx.MockTransport(handler),
    )
    fetcher = Fetcher(client=client)

    await fetcher.artist_index()
    assert "br" in seen_headers["accept-encoding"]
    assert "gzip" in seen_headers["accept-encoding"]


async def test_fetcher_does_not_retry_4xx() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)

    with pytest.raises(httpx.HTTPStatusError):
        await fetcher.artist_index()
    assert calls["n"] == 1  # 404 is permanent — not retried
