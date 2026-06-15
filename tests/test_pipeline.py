from pathlib import Path

import httpx

from letras.pipeline import run
from letras.source.fetcher import Fetcher
from letras.store.corpus_store import CorpusStore

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_fetcher() -> Fetcher:
    index = (FIXTURES / "artist_index.html").read_text(encoding="utf-8")
    artist = (FIXTURES / "artist_page.html").read_text(encoding="utf-8")
    song = (FIXTURES / "song_page.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "todosartistas" in path:
            return httpx.Response(200, text=index)
        if path.strip("/").count("/") == 0:  # /<artist>/
            return httpx.Response(200, text=artist)
        return httpx.Response(200, text=song)  # /<artist>/<song>/

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    return Fetcher(client=client)


def test_run_populates_store_for_one_artist() -> None:
    store = CorpusStore(":memory:")

    run(_fixture_fetcher(), store, only_slug="1-igreja-batista-em-trindade")

    rows = list(store.iter_export())
    assert len(rows) == 10  # the artist fixture lists 10 songs
    artist, _song, content = rows[0]
    assert artist.name == "1° Igreja Batista Em Trindade"
    assert content.startswith("Ao Rei dos reis")
    assert {song.name for _, song, _ in rows} >= {"Consagração", "Jeová Jireh"}
