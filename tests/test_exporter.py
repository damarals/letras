import zipfile
from pathlib import Path

from letras.domain.entities import Artist, Song
from letras.domain.policy import load_policy
from letras.release.exporter import export_release
from letras.store.corpus_store import CorpusStore

GOOD = "Louvarei ao Senhor de todo o meu coração e exaltarei o Teu nome " * 4


def test_export_release_includes_only_admitted_songs(tmp_path: Path) -> None:
    db_path = tmp_path / "corpus.db"
    store = CorpusStore(db_path)
    artist_id = store.upsert_artist(Artist(name="Aline Barros", slug="aline-barros"))
    good_id = store.upsert_song(Song(name="Consagração", slug="44039"), artist_id)
    store.set_lyrics(good_id, GOOD, "pt", len(GOOD))
    short_id = store.upsert_song(Song(name="Short", slug="s1"), artist_id)
    store.set_lyrics(short_id, "curta", "pt", 5)  # < 100 chars -> rejected
    out = tmp_path / "dist"

    export_release(store, db_path, out, date="20260615", policy=load_policy())

    assert (out / "corpus.db").exists()
    with zipfile.ZipFile(out / "lyrics.zip") as archive:
        names = archive.namelist()
    assert "Aline Barros - Consagração.txt" in names
    assert "Aline Barros - Short.txt" not in names

    notes = (out / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "1 songs from 1 artists" in notes
