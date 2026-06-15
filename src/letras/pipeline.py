"""Orchestration: discover -> scrape -> store. One pipeline (ADR-0003).

Fetching and parsing run concurrently on a single ``asyncio`` event loop, across
both artists and songs; a ``Semaphore`` bounds how many requests are in flight
at once. SQLite writes stay on the loop (the store holds one connection, and
there is only one thread). Full-vs-incremental is a selection predicate, not a
separate runner.
"""

import asyncio

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


async def run(
    fetcher: Fetcher,
    store: CorpusStore,
    *,
    workers: int = 8,
    incremental: bool = False,
    only_slug: str | None = None,
    max_songs: int | None = None,
) -> None:
    artists = parse_artist_index(await fetcher.artist_index())
    if only_slug is not None:
        artists = [a for a in artists if a.slug == only_slug]

    artist_ids = {a.slug: store.upsert_artist(a) for a in artists}
    known: dict[str, set[str]] = (
        {a.slug: store.known_song_slugs(artist_ids[a.slug]) for a in artists}
        if incremental
        else {}
    )

    sem = asyncio.Semaphore(workers)

    # Phase 1 (concurrent): fetch + parse each artist page into a flat work list.
    async def list_songs(artist: Artist) -> tuple[Artist, list[Song]]:
        async with sem:
            try:
                html = await fetcher.artist_page(artist.slug)
            except httpx.HTTPError:
                return artist, []  # dead/unreachable artist page -> skip it
        songs = parse_artist_songs(html)
        if incremental:
            songs = [s for s in songs if s.slug not in known[artist.slug]]
        if max_songs is not None:
            songs = songs[:max_songs]
        return artist, songs

    listed: list[tuple[Artist, list[Song]]] = await asyncio.gather(
        *(list_songs(artist) for artist in artists)
    )
    work: list[tuple[Artist, Song]] = [
        (artist, song) for artist, songs in listed for song in songs
    ]

    # Phase 2 (concurrent): fetch + parse + label each song; store on this loop.
    async def scrape(
        item: tuple[Artist, Song],
    ) -> tuple[Artist, Song, str, str] | None:
        artist, song = item
        async with sem:
            try:
                page = await fetcher.song_page(artist.slug, song.slug)
            except httpx.HTTPError:
                return None  # a dead page never aborts the run
        try:
            content = parse_song(page)
        except ParseError:
            return None  # a malformed page never aborts the run
        return artist, song, content, detect_language(content)

    for start in range(0, len(work), _BATCH):
        batch = work[start : start + _BATCH]
        results: list[tuple[Artist, Song, str, str] | None] = await asyncio.gather(
            *(scrape(item) for item in batch)
        )
        for result in results:
            if result is None:
                continue
            artist, song, content, language = result
            song_id = store.upsert_song(song, artist_ids[artist.slug])
            store.set_lyrics(
                song_id, content, language=language, char_count=len(content)
            )
