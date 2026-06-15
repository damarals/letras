"""HTTP access to the source. Thin and side-effectful; the seam against parser.

Retries, rate-limiting, and concurrency are added in a later slice; this is the
minimal happy-path client.
"""

import httpx

_BASE_URL = "https://www.letras.mus.br"
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_INDEX_PATH = "/estilos/gospelreligioso/todosartistas.html"


class Fetcher:
    def __init__(
        self, base_url: str = _BASE_URL, *, client: httpx.Client | None = None
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            headers={"User-Agent": _USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )

    def _get(self, path: str) -> str:
        response = self._client.get(path)
        response.raise_for_status()
        return response.text

    def artist_index(self) -> str:
        return self._get(_INDEX_PATH)

    def artist_page(self, slug: str) -> str:
        return self._get(f"/{slug}/")

    def song_page(self, artist_slug: str, song_slug: str) -> str:
        return self._get(f"/{artist_slug}/{song_slug}/")

    def close(self) -> None:
        self._client.close()
