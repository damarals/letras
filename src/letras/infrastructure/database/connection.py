import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg


class PostgresConnection:
    def __init__(
        self, user: str, password: str, database: str, host: str, port: int = 5432
    ):
        self._conn_params = {
            "user": user,
            "password": password,
            "database": database,
            "host": host,
            "port": port,
        }
        self._pool = None
        self._logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize connection pool"""
        if not self._pool:
            try:
                self._pool = await asyncpg.create_pool(
                    **self._conn_params, min_size=5, max_size=20
                )
                await self._init_schema()
            except Exception as e:
                self._logger.error(f"Database initialization failed: {e}")
                raise

    async def _init_schema(self):
        """Initialize database schema"""
        async with self.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artists (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) UNIQUE NOT NULL,
                    views INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS songs (
                    id SERIAL PRIMARY KEY,
                    artist_id INTEGER NOT NULL REFERENCES artists(id),
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) NOT NULL,
                    views INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (artist_id, slug)
                );

                CREATE TABLE IF NOT EXISTS lyrics (
                    id SERIAL PRIMARY KEY,
                    song_id INTEGER NOT NULL REFERENCES songs(id) UNIQUE,
                    content TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_artists_slug ON artists(slug);
                CREATE INDEX IF NOT EXISTS idx_songs_artist_id ON songs(artist_id);
            """
            )

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a database connection"""
        if not self._pool:
            await self.initialize()

        async with self._pool.acquire() as connection:
            yield connection

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Transaction context manager"""
        async with self.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
