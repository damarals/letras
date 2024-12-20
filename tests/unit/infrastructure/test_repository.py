from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)


class TestPostgresRepository:
    @pytest.fixture
    def mock_db_connection(self):
        """Mock the actual database connection that executes queries"""
        connection = MagicMock()
        connection.fetch = AsyncMock()
        connection.fetchrow = AsyncMock()
        connection.execute = AsyncMock()
        return connection

    @pytest.fixture
    def mock_connection(self, mock_db_connection):
        """Mock the connection manager with context support"""
        connection = MagicMock()

        @asynccontextmanager
        async def acquire():
            yield mock_db_connection

        connection.acquire = acquire
        return connection

    @pytest.fixture
    def repository(self, mock_connection):
        return PostgresRepository(mock_connection)

    @pytest.mark.asyncio
    async def test_get_all_artists(self, repository, mock_db_connection):
        # Setup mock data
        mock_artist_data = {
            "id": 1,
            "name": "Test",
            "slug": "test",
            "views": 1000,
            "added_date": datetime.now(),
        }
        mock_db_connection.fetch.return_value = [mock_artist_data]

        # Execute
        artists = await repository.get_all_artists()

        # Verify
        assert len(artists) == 1
        assert isinstance(artists[0], Artist)
        assert artists[0].id == 1
        mock_db_connection.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_artist(self, repository, mock_db_connection):
        # Setup mock data
        mock_artist_data = {
            "id": 1,
            "name": "Test",
            "slug": "test",
            "views": 1000,
            "added_date": datetime.now(),
        }
        mock_db_connection.fetchrow.return_value = mock_artist_data

        # Execute
        artist = await repository.add_artist(
            Artist(name="Test", slug="test", views=1000)
        )

        # Verify
        assert isinstance(artist, Artist)
        assert artist.id == 1
        mock_db_connection.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_songs_by_artist(self, repository, mock_db_connection):
        # Setup mock data
        mock_song_data = {
            "id": 1,
            "name": "Test Song",
            "slug": "test-song",
            "artist_id": 1,
            "views": 500,
            "added_date": datetime.now(),
        }
        mock_db_connection.fetch.return_value = [mock_song_data]

        # Execute
        songs = await repository.get_songs_by_artist(1)

        # Verify
        assert len(songs) == 1
        assert isinstance(songs[0], Song)
        assert songs[0].artist_id == 1
        mock_db_connection.fetch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_lyrics(self, repository, mock_db_connection):
        # Setup mock data
        mock_lyrics_data = {
            "id": 1,
            "song_id": 1,
            "content": "Test lyrics",
            "last_updated": datetime.now(),
        }
        mock_db_connection.fetchrow.return_value = mock_lyrics_data

        # Execute
        lyrics = await repository.add_lyrics(Lyrics(song_id=1, content="Test lyrics"))

        # Verify
        assert isinstance(lyrics, Lyrics)
        assert lyrics.id == 1
        mock_db_connection.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transaction_handling(self, repository, mock_db_connection):
        # Setup mock to raise an exception
        error_msg = "DB Error"
        mock_db_connection.fetch.side_effect = Exception(error_msg)

        # Verify exception is raised
        with pytest.raises(Exception) as exc:
            await repository.get_all_artists()
        assert str(exc.value) == error_msg

    @pytest.mark.asyncio
    async def test_duplicate_handling(self, repository, mock_db_connection):
        # Setup mock to raise a duplicate key error
        mock_db_connection.fetchrow.side_effect = Exception("duplicate key value")

        # Verify exception is raised
        with pytest.raises(Exception):
            await repository.add_artist(Artist(name="Test", slug="test"))
