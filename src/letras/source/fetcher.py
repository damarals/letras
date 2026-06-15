"""HTTP access to the source. Side-effectful; the seam against parser.

Adds retries (tenacity), a politeness delay, and a bounded thread pool for
fetching many pages at once.
"""

import time
from concurrent.futures import ThreadPoolExecutor

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
        max_workers: int = 8,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        self._delay = delay
        self._max_workers = max_workers
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

    def fetch_many(self, paths: list[str]) -> list[str]:
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            return list(pool.map(self._get, paths))

    def artist_index(self) -> str:
        return self._get(_INDEX_PATH)

    def artist_page(self, slug: str) -> str:
        return self._get(f"/{slug}/")

    def song_page(self, artist_slug: str, song_slug: str) -> str:
        return self._get(f"/{artist_slug}/{song_slug}/")

    def song_pages(self, artist_slug: str, song_slugs: list[str]) -> list[str]:
        return self.fetch_many([f"/{artist_slug}/{slug}/" for slug in song_slugs])

    def close(self) -> None:
        self._client.close()
