"""HTTP access to the source. A side-effectful single-request client; the seam
against the parser. Concurrency is owned by the pipeline.

Adds retries (tenacity) and a politeness delay between requests.
"""

import time

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_BASE_URL = "https://www.letras.mus.br"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_INDEX_PATH = "/estilos/gospelreligioso/todosartistas.html"


class Fetcher:
    def __init__(
        self,
        base_url: str = _BASE_URL,
        *,
        client: httpx.Client | None = None,
        delay: float = 0.0,
        max_attempts: int = 3,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        self._delay = delay
        self._retrying = Retrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.1, max=2),
            retry=retry_if_exception_type(
                (httpx.HTTPStatusError, httpx.TransportError)
            ),
            reraise=True,
        )

    def _fetch(self, path: str) -> str:
        response = self._client.get(path)
        response.raise_for_status()
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
