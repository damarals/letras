from letras.domain.entities import Artist, Song
from letras.store.corpus_store import CorpusStore


def test_corpus_store_round_trips_artist_song_and_lyrics() -> None:
    store = CorpusStore(":memory:")

    artist_id = store.upsert_artist(Artist(name="Aline Barros", slug="aline-barros"))
    song_id = store.upsert_song(Song(name="Consagração", slug="44039"), artist_id)
    store.set_lyrics(song_id, content="Ao Rei dos reis", language="pt", char_count=15)

    exported = list(store.iter_export())

    assert exported == [
        (
            Artist(name="Aline Barros", slug="aline-barros"),
            Song(name="Consagração", slug="44039"),
            "Ao Rei dos reis",
        )
    ]


def test_known_song_slugs_returns_only_that_artists_slugs() -> None:
    store = CorpusStore(":memory:")
    aline = store.upsert_artist(Artist(name="Aline Barros", slug="aline-barros"))
    store.upsert_song(Song(name="Consagração", slug="44039"), aline)
    store.upsert_song(Song(name="Jeová Jireh", slug="jeova-jireh"), aline)
    other = store.upsert_artist(Artist(name="Other", slug="other"))
    store.upsert_song(Song(name="X", slug="x1"), other)

    assert store.known_song_slugs(aline) == {"44039", "jeova-jireh"}
