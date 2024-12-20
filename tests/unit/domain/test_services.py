from unittest.mock import AsyncMock, Mock, patch

import pytest

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.domain.services.lyrics_service import LyricsService
from letras.infrastructure.web.scraper import ScrapeResult


class TestLyricsService:
    @pytest.fixture
    def mock_repository(self):
        repo = Mock()
        repo.get_artist_by_slug = AsyncMock()
        repo.add_artist = AsyncMock()
        repo.update_artist_views = AsyncMock()
        repo.get_songs_by_artist = AsyncMock(return_value=[])
        repo.get_lyrics_by_song = AsyncMock()
        repo.add_song = AsyncMock()
        repo.add_lyrics = AsyncMock()
        return repo

    @pytest.fixture
    def mock_language_service(self):
        service = Mock()
        service.is_portuguese = Mock(return_value=True)
        return service

    @pytest.fixture
    def mock_scraper(self):
        scraper = Mock()
        scraper.get_artist_details = AsyncMock()
        scraper.get_artist_songs = AsyncMock()
        scraper.get_song_details = AsyncMock()
        return scraper

    @pytest.fixture
    def service(self, mock_repository, mock_language_service, mock_scraper):
        return LyricsService(
            repository=mock_repository,
            language_service=mock_language_service,
            scraper=mock_scraper,
        )

    @pytest.mark.asyncio
    async def test_process_new_artist(self, service, mock_repository, mock_scraper):
        # Setup
        artist = Artist(name="Test", slug="test")
        scrape_result = ScrapeResult(content="", views=1000)
        processed_artist = Artist(name="Test", slug="test", views=1000, id=1)

        mock_scraper.get_artist_details.return_value = scrape_result
        mock_repository.get_artist_by_slug.return_value = None
        mock_repository.add_artist.return_value = processed_artist

        # Execute
        result = await service.process_artist(artist)

        # Verify
        assert result == processed_artist
        mock_repository.get_artist_by_slug.assert_awaited_once_with("test")
        mock_repository.add_artist.assert_awaited_once()
        mock_repository.update_artist_views.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_existing_artist(
        self, service, mock_repository, mock_scraper
    ):
        # Setup
        existing = Artist(name="Test", slug="test", views=500, id=1)
        scrape_result = ScrapeResult(content="", views=1000)

        mock_scraper.get_artist_details.return_value = scrape_result
        mock_repository.get_artist_by_slug.return_value = existing

        # Execute
        result = await service.process_artist(Artist(name="Test", slug="test"))

        # Verify
        assert result == existing
        mock_repository.update_artist_views.assert_awaited_once_with(1, 1000)

    @pytest.mark.asyncio
    async def test_process_songs_new(self, service, mock_repository, mock_scraper):
        # Setup
        artist = Artist(name="Test", slug="test", id=1)
        mock_scraper.get_artist_songs.return_value = [
            Song(name="Song 1", slug="song-1", artist_id=1),
            Song(name="Song 2", slug="song-2", artist_id=1),
        ]

        # Execute
        result = await service.process_songs(artist)

        # Verify
        assert len(result) == 2
        mock_scraper.get_artist_songs.assert_awaited_once_with(artist)
        mock_repository.get_songs_by_artist.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_process_lyrics(
        self, service, mock_repository, mock_scraper, mock_language_service
    ):
        # Setup
        artist = Artist(name="Test", slug="test", id=1)
        song = Song(name="Test Song", slug="test-song", artist_id=1)
        scrape_result = ScrapeResult(content="Test lyrics", views=100)
        processed_song = Song(name="Test Song", slug="test-song", artist_id=1, id=1)
        processed_lyrics = Lyrics(song_id=1, content="Test lyrics", id=1)

        mock_scraper.get_song_details.return_value = scrape_result
        mock_repository.add_song.return_value = processed_song
        mock_repository.add_lyrics.return_value = processed_lyrics
        mock_language_service.is_portuguese.return_value = True

        # Execute
        result = await service.process_lyrics(artist, song)

        # Verify
        assert result == processed_lyrics
        mock_scraper.get_song_details.assert_awaited_once_with(artist, song)
        mock_repository.add_lyrics.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, service, mock_scraper):
        # Setup
        mock_scraper.get_artist_details.side_effect = Exception("Network error")

        # Execute & Verify
        with pytest.raises(Exception) as exc:
            await service.process_artist(Artist(name="Test", slug="test"))
        assert "Network error" in str(exc.value)
