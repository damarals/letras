"""Orchestration: discover → scrape → store. One pipeline (ADR-0003).

Full-vs-incremental selection and language labelling arrive in later slices;
this skeleton scrapes (optionally a single artist) and stores raw.
"""

from letras.domain.language import detect_language
from letras.source.fetcher import Fetcher
from letras.source.parser import (
    ParseError,
    parse_artist_index,
    parse_artist_songs,
    parse_song,
)
from letras.store.corpus_store import CorpusStore


def run(
    fetcher: Fetcher,
    store: CorpusStore,
    *,
    incremental: bool = False,
    only_slug: str | None = None,
    max_songs: int | None = None,
) -> None:
    artists = parse_artist_index(fetcher.artist_index())
    if only_slug is not None:
        artists = [a for a in artists if a.slug == only_slug]

    for artist in artists:
        artist_id = store.upsert_artist(artist)
        songs = parse_artist_songs(fetcher.artist_page(artist.slug))
        if incremental:
            known = store.known_song_slugs(artist_id)
            songs = [song for song in songs if song.slug not in known]
        if max_songs is not None:
            songs = songs[:max_songs]
        pages = fetcher.song_pages(artist.slug, [song.slug for song in songs])
        for song, html in zip(songs, pages, strict=True):
            song_id = store.upsert_song(song, artist_id)
            try:
                content = parse_song(html)
            except ParseError:
                continue  # skip a single malformed page; don't abort the run
            store.set_lyrics(
                song_id,
                content,
                language=detect_language(content),
                char_count=len(content),
            )
