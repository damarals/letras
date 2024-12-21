import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.runners.full import FullRunner


class TestBaseRunner:
    @pytest.fixture
    def db_config(self):
        return {
            "host": "test-host",
            "port": 5432,
            "database": "test-db",
            "user": "test-user",
            "password": "test-pass",
        }

    @pytest.fixture
    async def mock_repository(self):
        repo = MagicMock()
        repo.get_all_artists = AsyncMock(return_value=[])
        repo.get_songs_by_artist = AsyncMock(return_value=[])
        repo.get_artist_by_id = AsyncMock()
        repo.get_song_by_id = AsyncMock()
        return repo

    @pytest.fixture
    async def mock_service(self):
        service = MagicMock()
        service.process_artist = AsyncMock()
        service.process_songs = AsyncMock()
        service.process_lyrics = AsyncMock()
        return service

    @pytest.fixture
    async def mock_scraper(self):
        scraper = MagicMock()
        scraper.get_all_artists = AsyncMock(return_value=[])
        scraper.get_artist_details = AsyncMock()
        scraper.get_artist_songs = AsyncMock()
        return scraper

    @pytest.fixture
    async def runner(self, mock_service, mock_scraper, mock_repository, db_config):
        runner = FullRunner(
            db_config=db_config,
            base_url="http://test.com",
            verbose=False
        )

        runner.service = mock_service
        runner.scraper = mock_scraper
        runner.repository = mock_repository

        return runner

    @pytest.mark.asyncio
    async def test_process_songs_concurrent(self, runner, mock_service):
        artists = [
            Artist(name=f"Artist {i}", slug=f"artist-{i}", id=i) for i in range(3)
        ]
        songs = [
            Song(name=f"Song {i}", slug=f"song-{i}", artist_id=i) for i in range(3)
        ]
        mock_service.process_songs.return_value = songs

        result = await runner.process_songs(artists)
        assert len(result) == 9  # 3 songs * 3 artists
        assert mock_service.process_songs.await_count == 3

    @pytest.mark.asyncio
    async def test_process_lyrics_concurrent(self, runner, mock_service):
        artists = [Artist(name="Test", slug="test", id=1)]
        songs = [
            Song(name=f"Song {i}", slug=f"song-{i}", artist_id=1) for i in range(3)
        ]
        lyrics = Lyrics(song_id=1, content="Test lyrics")
        mock_service.process_lyrics.return_value = lyrics

        result = await runner.process_lyrics(artists, songs)
        assert len(result) == 3
        assert mock_service.process_lyrics.await_count == 3

    @pytest.mark.asyncio
    async def test_create_release(self, runner, tmp_path, mock_repository, db_config):
        # Setup dos diretórios
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Setup dos mocks para dois artistas diferentes
        mock_songs = {
            1: Song(id=1, name="Test Song 1", slug="test-song-1", artist_id=1),
            2: Song(id=2, name="Test Song 2", slug="test-song-2", artist_id=2),
        }
        mock_artists = {
            1: Artist(id=1, name="Test Artist 1", slug="test-artist-1", views=1000),
            2: Artist(id=2, name="Test Artist 2", slug="test-artist-2", views=2000),
        }

        mock_repository.get_song_by_id.side_effect = lambda x: mock_songs.get(x)
        mock_repository.get_artist_by_id.side_effect = lambda x: mock_artists.get(x)

        lyrics_list = [
            Lyrics(song_id=1, content="Test lyrics 1"),
            Lyrics(song_id=2, content="Test lyrics 2"),
        ]

        # Mock subprocess for pg_dump
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        
        # Mock both PostgresUtils class and subprocess
        mock_postgres_utils = MagicMock()
        mock_postgres_utils.create_backup = AsyncMock(return_value=str(temp_dir / "backup.sql"))

        with patch('asyncio.create_subprocess_exec', AsyncMock(return_value=mock_process)), \
             patch('letras.runners.base.PostgresUtils', MagicMock(return_value=mock_postgres_utils)) as mock_utils_class:
            # Execute
            await runner.create_release(
                lyrics_list=lyrics_list, 
                output_dir=str(tmp_path), 
                temp_dir=str(temp_dir)
            )

            # Verify PostgresUtils was created with correct config
            mock_utils_class.assert_called_once_with(db_config)
            
            # Verify backup was created
            mock_postgres_utils.create_backup.assert_called_once_with(str(temp_dir))

            # Verify files
            release_notes = tmp_path / "RELEASE_NOTES.md"
            assert release_notes.exists(), "Release notes file should exist"

            # Verify release notes content
            notes_content = release_notes.read_text()
            assert "2 new songs" in notes_content, "Should mention number of songs"
            assert "2 artists" in notes_content, "Should mention number of artists"
            assert "Test Artist 2" in notes_content, "Should mention highest viewed artist"

            # Verify zip file
            zip_files = list(tmp_path.glob("*.zip"))
            assert len(zip_files) == 1, "Should create exactly one zip file"

    @pytest.mark.asyncio
    async def test_error_handling(self, runner, mock_scraper):
        mock_scraper.get_all_artists.side_effect = Exception("Test error")

        with pytest.raises(Exception) as exc:
            await runner.process_artists()

        assert "Test error" in str(exc.value)