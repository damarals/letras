"""Orchestration: discover -> scrape -> store. One pipeline (ADR-0003).

Fetching and parsing run concurrently across both artists and songs; SQLite
writes stay on the calling thread, since the store holds a single connection.
Full-vs-incremental is a selection predicate, not a separate runner.
"""

from concurrent.futures import ThreadPoolExecutor

import httpx

from letras.domain.entities import Artist, Song
from letras.domain.language import detect_language
from letras.source.fetcher import Fetcher
from letras.source.parser import (
    ParseError,
    parse_artist_index,
    parse_artist_songs,
    parse_song,
)
from letras.store.corpus_store import CorpusStore

_BATCH = 500


def run(
    fetcher: Fetcher,
    store: CorpusStore,
    *,
    workers: int = 8,
    incremental: bool = False,
    only_slug: str | None = None,
    max_songs: int | None = None,
) -> None:
    artists = parse_artist_index(fetcher.artist_index())
    if only_slug is not None:
        artists = [a for a in artists if a.slug == only_slug]

    artist_ids = {a.slug: store.upsert_artist(a) for a in artists}
    known: dict[str, set[str]] = (
        {a.slug: store.known_song_slugs(artist_ids[a.slug]) for a in artists}
        if incremental
        else {}
    )

    # Phase 1 (concurrent): fetch + parse each artist page into a flat work list.
    def list_songs(artist: Artist) -> tuple[Artist, list[Song]]:
        try:
            html = fetcher.artist_page(artist.slug)
        except httpx.HTTPError:
            return artist, []  # dead/unreachable artist page -> skip it
        songs = parse_artist_songs(html)
        if incremental:
            songs = [s for s in songs if s.slug not in known[artist.slug]]
        if max_songs is not None:
            songs = songs[:max_songs]
        return artist, songs

    work: list[tuple[Artist, Song]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for artist, songs in pool.map(list_songs, artists):
            work.extend((artist, song) for song in songs)

    # Phase 2 (concurrent): fetch + parse + label each song; store on this thread.
    def scrape(item: tuple[Artist, Song]) -> tuple[Artist, Song, str, str] | None:
        artist, song = item
        try:
            content = parse_song(fetcher.song_page(artist.slug, song.slug))
        except (httpx.HTTPError, ParseError):
            return None  # a dead or malformed page never aborts the run
        return artist, song, content, detect_language(content)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(work), _BATCH):
            for result in pool.map(scrape, work[start : start + _BATCH]):
                if result is None:
                    continue
                artist, song, content, language = result
                song_id = store.upsert_song(song, artist_ids[artist.slug])
                store.set_lyrics(
                    song_id, content, language=language, char_count=len(content)
                )
