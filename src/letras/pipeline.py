"""Orchestration: discover → scrape → store. One pipeline (ADR-0003).

Full-vs-incremental selection and language labelling arrive in later slices;
this skeleton scrapes (optionally a single artist) and stores raw.
"""

from letras.source.fetcher import Fetcher
from letras.source.parser import parse_artist_index, parse_artist_songs, parse_song
from letras.store.corpus_store import CorpusStore


def run(
    fetcher: Fetcher,
    store: CorpusStore,
    *,
    only_slug: str | None = None,
    max_songs: int | None = None,
) -> None:
    artists = parse_artist_index(fetcher.artist_index())
    if only_slug is not None:
        artists = [a for a in artists if a.slug == only_slug]

    for artist in artists:
        artist_id = store.upsert_artist(artist)
        songs = parse_artist_songs(fetcher.artist_page(artist.slug))
        if max_songs is not None:
            songs = songs[:max_songs]
        for song in songs:
            song_id = store.upsert_song(song, artist_id)
            content = parse_song(fetcher.song_page(artist.slug, song.slug))
            store.set_lyrics(
                song_id, content, language=None, char_count=len(content)
            )
