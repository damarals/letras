import zipfile
from pathlib import Path

from letras.domain.entities import Artist, Song
from letras.release.exporter import export_release
from letras.store.corpus_store import CorpusStore


def test_export_release_writes_db_zip_and_notes(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    store = CorpusStore(db_path)
    artist_id = store.upsert_artist(Artist(name="Aline Barros", slug="aline-barros"))
    song_id = store.upsert_song(Song(name="Consagração", slug="44039"), artist_id)
    store.set_lyrics(song_id, "Ao Rei dos reis\nDe gratos louvores", "pt", 33)
    out = tmp_path / "dist"

    export_release(store, db_path, out, date="20260615")

    assert (out / "corpus.db").exists()
    with zipfile.ZipFile(out / "lyrics-20260615.zip") as archive:
        assert "Aline Barros - Consagração.txt" in archive.namelist()
        body = archive.read("Aline Barros - Consagração.txt").decode("utf-8")
    assert body == "Consagração\nAline Barros\n\nAo Rei dos reis\nDe gratos louvores"

    notes = (out / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "Aline Barros (1 songs)" in notes
