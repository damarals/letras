from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from letras.domain.entities.artist import Artist
from letras.runners.full import FullRunner


class TestFullRunner:
    @pytest.fixture
    async def mock_repository(self):
        repo = MagicMock()
        repo.get_all_artists = AsyncMock(return_value=[])
        repo.get_artist_by_id = AsyncMock()
        return repo

    @pytest.fixture
    async def mock_service(self):
        service = MagicMock()
        service.process_artist = AsyncMock()
        service.process_songs = AsyncMock(return_value=[])
        service.process_lyrics = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    async def mock_scraper(self):
        scraper = MagicMock()
        scraper.get_all_artists = AsyncMock()
        scraper.get_artist_details = AsyncMock()
        return scraper

    @pytest.fixture
    async def runner(self, mock_service, mock_scraper, mock_repository):
        """Create runner and patch its initialize method"""
        runner = FullRunner(
            db_config={},  # Config vazio pois não vamos usar
            base_url="http://test.com",
            verbose=False,
        )

        # Substituir atributos com mocks
        runner.service = mock_service
        runner.scraper = mock_scraper
        runner.repository = mock_repository

        return runner

    @pytest.mark.asyncio
    async def test_process_artists(self, runner, mock_scraper, mock_service):
        # Setup
        artists = [Artist(name=f"Artist {i}", slug=f"artist-{i}") for i in range(3)]
        processed_artists = [
            Artist(name=f"Artist {i}", slug=f"artist-{i}", id=i) for i in range(3)
        ]

        mock_scraper.get_all_artists.return_value = artists
        mock_service.process_artist.side_effect = processed_artists

        # Execute
        result = await runner.process_artists()

        # Verify
        assert len(result) == 3
        assert all(a.id is not None for a in result)
        assert mock_scraper.get_all_artists.await_count == 1
        assert mock_service.process_artist.await_count == 3

    @pytest.mark.asyncio
    async def test_empty_artist_list(self, runner, mock_scraper):
        # Setup
        mock_scraper.get_all_artists.return_value = []

        # Execute
        result = await runner.process_artists()

        # Verify
        assert result == []
        assert mock_scraper.get_all_artists.await_count == 1

    @pytest.mark.asyncio
    async def test_error_handling(self, runner, mock_scraper):
        # Setup
        mock_scraper.get_all_artists.side_effect = Exception("Test error")

        # Execute & Verify
        with pytest.raises(Exception) as exc:
            await runner.process_artists()

        assert "Test error" in str(exc.value)
