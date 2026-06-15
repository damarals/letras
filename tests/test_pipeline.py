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


def test_incremental_run_skips_songs_already_in_corpus() -> None:
    index = (FIXTURES / "artist_index.html").read_text(encoding="utf-8")
    artist = (FIXTURES / "artist_page.html").read_text(encoding="utf-8")
    song = (FIXTURES / "song_page.html").read_text(encoding="utf-8")
    song_fetches: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "todosartistas" in path:
            return httpx.Response(200, text=index)
        if path.strip("/").count("/") == 0:
            return httpx.Response(200, text=artist)
        song_fetches.append(path)
        return httpx.Response(200, text=song)

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    fetcher = Fetcher(client=client)
    store = CorpusStore(":memory:")
    slug = "1-igreja-batista-em-trindade"

    run(fetcher, store, only_slug=slug)  # full: scrapes all 10 songs
    assert len(song_fetches) == 10

    run(fetcher, store, only_slug=slug, incremental=True)  # all known -> none
    assert len(song_fetches) == 10


def test_run_skips_song_whose_lyrics_fail_to_parse() -> None:
    index = (FIXTURES / "artist_index.html").read_text(encoding="utf-8")
    artist = (FIXTURES / "artist_page.html").read_text(encoding="utf-8")
    good_song = (FIXTURES / "song_page.html").read_text(encoding="utf-8")
    broken_song = "<html><body><h1>X</h1><p>no lyrics container</p></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "todosartistas" in path:
            return httpx.Response(200, text=index)
        if path.strip("/").count("/") == 0:
            return httpx.Response(200, text=artist)
        if path.endswith("/44039/"):  # one song page is malformed
            return httpx.Response(200, text=broken_song)
        return httpx.Response(200, text=good_song)

    client = httpx.Client(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    store = CorpusStore(":memory:")

    run(Fetcher(client=client), store, only_slug="1-igreja-batista-em-trindade")

    rows = list(store.iter_export())
    assert len(rows) == 9  # 10 songs, the malformed one is skipped
    assert all(song.slug != "44039" for _, song, _ in rows)
