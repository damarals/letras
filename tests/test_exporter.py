import zipfile
from pathlib import Path

from letras.domain.entities import Artist, Song
from letras.domain.policy import load_policy
from letras.release.exporter import _render_notes, export_release
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
    with zipfile.ZipFile(out / "letras.zip") as archive:
        names = archive.namelist()
    assert "Aline Barros - Consagração.txt" in names
    assert "Aline Barros - Short.txt" not in names

    notes = (out / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "| Músicas (admitidas) | 1 |" in notes
    assert "| Artistas | 1 |" in notes
    assert "| Coletadas (brutas) | 2 |" in notes  # Consagração ok, Short rejeitada


def test_render_notes_is_bounded_and_omits_per_artist_list() -> None:
    # GitHub rejects a release body over 125,000 chars. The corpus has
    # thousands of artists, so the notes must NOT list them one by one.
    rows = [
        (
            Artist(name=f"Artista {i:05d}", slug=f"a{i}"),
            Song(name=f"Canção {i}", slug=f"s{i}"),
            "lyric",
        )
        for i in range(8000)
    ]

    notes = _render_notes(rows, "20260616", scraped=9000)

    assert len(notes) < 125_000
    assert "Artista 04000" not in notes  # individual artists are not listed
    assert "| Músicas (admitidas) | 8.000 |" in notes  # PT thousands separator
    assert "| Coletadas (brutas) | 9.000 |" in notes


def test_export_zip_disambiguates_colliding_filenames(tmp_path: Path) -> None:
    # Two distinct songs can map to the same "Artist - Song.txt"; neither may be
    # silently dropped from the archive.
    db_path = tmp_path / "corpus.db"
    store = CorpusStore(db_path)
    artist_id = store.upsert_artist(Artist(name="Fulano", slug="fulano"))
    one = store.upsert_song(Song(name="Igual", slug="v1"), artist_id)
    store.set_lyrics(one, GOOD, "pt", len(GOOD))
    two = store.upsert_song(Song(name="Igual", slug="v2"), artist_id)
    store.set_lyrics(two, GOOD + " distinta", "pt", len(GOOD) + 9)
    out = tmp_path / "dist"

    export_release(store, db_path, out, date="20260616", policy=load_policy())

    with zipfile.ZipFile(out / "letras.zip") as archive:
        names = archive.namelist()
    assert len(names) == 2  # both songs written
    assert len(set(names)) == 2  # under distinct names — no silent overwrite
