import logging
from typing import List, Optional

from asyncpg import Connection

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.domain.repositories.lyrics_repository import LyricsRepository
from letras.infrastructure.database.connection import PostgresConnection


class PostgresRepository(LyricsRepository):
    def __init__(self, conn: PostgresConnection):
        self._conn = conn
        self._logger = logging.getLogger(__name__)
        self._current_transaction: Optional[Connection] = None

    async def get_all_artists(self) -> List[Artist]:
        if self._current_transaction:
            rows = await self._current_transaction.fetch(
                "SELECT * FROM artists ORDER BY name"
            )
            return [Artist(**row) for row in rows]

        async with self._conn.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM artists ORDER BY name")
            return [Artist(**row) for row in rows]

    async def get_artist_by_slug(self, slug: str) -> Optional[Artist]:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                "SELECT * FROM artists WHERE slug = $1", slug
            )
            return Artist(**row) if row else None

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM artists WHERE slug = $1", slug)
            return Artist(**row) if row else None

    async def get_artist_by_id(self, artist_id: int) -> Optional[Artist]:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                "SELECT * FROM artists WHERE id = $1", artist_id
            )
            return Artist(**row) if row else None

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM artists WHERE id = $1", artist_id)
            return Artist(**row) if row else None

    async def add_artist(self, artist: Artist) -> Artist:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                """
                INSERT INTO artists (name, slug, views)
                VALUES ($1, $2, $3)
                ON CONFLICT (slug) DO UPDATE 
                    SET views = EXCLUDED.views
                RETURNING *
            """,
                artist.name,
                artist.slug,
                artist.views,
            )
            return Artist(**row)

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO artists (name, slug, views)
                VALUES ($1, $2, $3)
                ON CONFLICT (slug) DO UPDATE 
                    SET views = EXCLUDED.views
                RETURNING *
            """,
                artist.name,
                artist.slug,
                artist.views,
            )
            return Artist(**row)

    async def update_artist_views(self, artist_id: int, views: int) -> None:
        if self._current_transaction:
            await self._current_transaction.execute(
                """
                UPDATE artists SET views = $2
                WHERE id = $1
            """,
                artist_id,
                views,
            )
            return

        async with self._conn.acquire() as conn:
            await conn.execute(
                """
                UPDATE artists SET views = $2
                WHERE id = $1
            """,
                artist_id,
                views,
            )

    async def get_songs_by_artist(self, artist_id: int) -> List[Song]:
        if self._current_transaction:
            rows = await self._current_transaction.fetch(
                "SELECT * FROM songs WHERE artist_id = $1", artist_id
            )
            return [Song(**row) for row in rows]

        async with self._conn.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM songs WHERE artist_id = $1", artist_id
            )
            return [Song(**row) for row in rows]

    async def get_song_by_id(self, song_id: int) -> Optional[Song]:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                "SELECT * FROM songs WHERE id = $1", song_id
            )
            return Song(**row) if row else None

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM songs WHERE id = $1", song_id)
            return Song(**row) if row else None

    async def add_song(self, song: Song) -> Song:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                """
                INSERT INTO songs (name, slug, artist_id, views)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (artist_id, slug) DO UPDATE 
                    SET views = EXCLUDED.views
                RETURNING *
            """,
                song.name,
                song.slug,
                song.artist_id,
                song.views,
            )
            return Song(**row)

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO songs (name, slug, artist_id, views)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (artist_id, slug) DO UPDATE 
                    SET views = EXCLUDED.views
                RETURNING *
            """,
                song.name,
                song.slug,
                song.artist_id,
                song.views,
            )
            return Song(**row)

    async def add_lyrics(self, lyrics: Lyrics) -> Lyrics:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                """
                INSERT INTO lyrics (song_id, content)
                VALUES ($1, $2)
                ON CONFLICT (song_id) DO UPDATE 
                    SET content = EXCLUDED.content,
                        last_updated = CURRENT_TIMESTAMP
                RETURNING *
            """,
                lyrics.song_id,
                lyrics.content,
            )
            return Lyrics(**row)

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO lyrics (song_id, content)
                VALUES ($1, $2)
                ON CONFLICT (song_id) DO UPDATE 
                    SET content = EXCLUDED.content,
                        last_updated = CURRENT_TIMESTAMP
                RETURNING *
            """,
                lyrics.song_id,
                lyrics.content,
            )
            return Lyrics(**row)

    async def get_lyrics_by_song(self, song_id: int) -> Optional[Lyrics]:
        if self._current_transaction:
            row = await self._current_transaction.fetchrow(
                "SELECT * FROM lyrics WHERE song_id = $1", song_id
            )
            return Lyrics(**row) if row else None

        async with self._conn.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM lyrics WHERE song_id = $1", song_id
            )
            return Lyrics(**row) if row else None
