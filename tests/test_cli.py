import zipfile
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from letras.cli import app
from letras.domain.entities import Artist, Song
from letras.source.fetcher import Fetcher
from letras.store.corpus_store import CorpusStore

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def _fixture_fetcher() -> Fetcher:
    index = (FIXTURES / "artist_index.html").read_text(encoding="utf-8")
    artist = (FIXTURES / "artist_page.html").read_text(encoding="utf-8")
    song = (FIXTURES / "song_page.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "todosartistas" in path:
            return httpx.Response(200, text=index)
        if path.strip("/").count("/") == 0:
            return httpx.Response(200, text=artist)
        return httpx.Response(200, text=song)

    client = httpx.AsyncClient(
        base_url="https://letras.test", transport=httpx.MockTransport(handler)
    )
    return Fetcher(client=client)


def test_run_command_populates_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("letras.cli.Fetcher", lambda *a, **k: _fixture_fetcher())
    db = tmp_path / "corpus.db"

    result = runner.invoke(
        app,
        [
            "run",
            "--artist",
            "1-igreja-batista-em-trindade",
            "--corpus",
            str(db),
            "--max-songs",
            "3",
        ],
    )

    assert result.exit_code == 0, result.output
    store = CorpusStore(db)
    rows = list(store.iter_export())
    store.close()
    assert len(rows) == 3


def test_export_command_writes_release(tmp_path: Path) -> None:
    db = tmp_path / "corpus.db"
    store = CorpusStore(db)
    artist_id = store.upsert_artist(Artist(name="Aline Barros", slug="aline-barros"))
    song_id = store.upsert_song(Song(name="Consagração", slug="44039"), artist_id)
    content = "Louvarei ao Senhor de todo o meu coração e exaltarei o Teu nome " * 4
    store.set_lyrics(song_id, content, "pt", len(content))
    store.close()
    out = tmp_path / "dist"

    result = runner.invoke(app, ["export", "--corpus", str(db), "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert (out / "corpus.db").exists()
    zip_path = out / "letras-txt.zip"
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        assert "Aline Barros - Consagração.txt" in archive.namelist()
    assert (out / "RELEASE_NOTES.md").exists()
