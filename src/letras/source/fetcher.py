"""HTTP access to the source. A side-effectful single-request client; the seam
against the parser. Concurrency is owned by the pipeline.

Transport choices that make a cold seed fast *and* a good citizen of the
source site:

- **HTTP/2 + a warm keepalive pool.** Hundreds of thousands of requests ride a
  handful of long-lived, multiplexed connections instead of one socket per
  request. Faster for us, and far gentler on the server (fewer connections,
  fewer TLS handshakes).
- **Compression** (gzip/brotli) negotiated via ``Accept-Encoding`` — the
  source serves brotli, roughly a 5-10x byte reduction on these pages.
- **A shared token-bucket rate limiter with AIMD backoff** instead of a crude
  per-request ``sleep``: a precise global req/s ceiling that *adapts*, honoring
  ``Retry-After`` and backing off on ``429``/``503`` so the site never needs to
  ban us. See ``rate_limiter.py``.

The legacy fixed ``delay`` is kept as an optional extra pause; pacing is
otherwise governed by the limiter.
"""

import time

import httpx
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from letras.source.rate_limiter import RateLimiter

_BASE_URL = "https://www.letras.mus.br"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_INDEX_PATH = "/estilos/gospelreligioso/todosartistas.html"

# Status codes that mean "you are going too fast" rather than "this is broken".
# We honor these explicitly (Retry-After + AIMD backoff) instead of treating
# them as generic transient errors.
_THROTTLE_CODES = frozenset({429, 503})
# Transient statuses worth retrying. Permanent 4xx (404, 403, 410, …) fail fast.
_RETRY_CODES = frozenset({429, 500, 502, 503, 504})


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRY_CODES
    return False


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header. Supports the delta-seconds form; an
    HTTP-date form (or anything unparseable) yields ``None`` so the caller
    falls back to the limiter's own backoff."""
    if value is None:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


class Fetcher:
    def __init__(
        self,
        base_url: str = _BASE_URL,
        *,
        client: httpx.Client | None = None,
        delay: float = 0.0,
        max_attempts: int = 3,
        http2: bool = True,
        max_connections: int = 16,
        max_keepalive_connections: int = 16,
        keepalive_expiry: float = 30.0,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept-Encoding": "gzip, deflate, br",
            },
            timeout=30.0,
            follow_redirects=True,
            http2=http2,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            ),
        )
        self._delay = delay
        self._limiter = rate_limiter
        self._retrying = Retrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.1, max=2),
            retry=retry_if_exception(_should_retry),
            reraise=True,
        )

    def _fetch(self, path: str) -> str:
        """One attempt: acquire a rate token, issue the request, and feed the
        outcome back to the limiter (backoff on throttle, ramp on success).

        On ``429``/``503`` we read ``Retry-After``, tell the limiter to back
        off (and sleep that long), then raise ``HTTPStatusError`` so tenacity
        retries the attempt at the now-reduced rate.
        """
        if self._limiter is not None:
            self._limiter.acquire()
        response = self._client.get(path)
        if response.status_code in _THROTTLE_CODES and self._limiter is not None:
            self._limiter.on_throttled(
                _parse_retry_after(response.headers.get("Retry-After"))
            )
        response.raise_for_status()  # throttle codes are 4xx/5xx -> raises here
        if self._limiter is not None:
            self._limiter.on_success()
        return response.text

    def _get(self, path: str) -> str:
        body: str = self._retrying(self._fetch, path)
        if self._delay:
            time.sleep(self._delay)
        return body

    def artist_index(self) -> str:
        return self._get(_INDEX_PATH)

    def artist_page(self, slug: str) -> str:
        return self._get(f"/{slug}/")

    def song_page(self, artist_slug: str, song_slug: str) -> str:
        return self._get(f"/{artist_slug}/{song_slug}/")

    def close(self) -> None:
        self._client.close()
