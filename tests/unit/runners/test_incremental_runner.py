from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from letras.domain.entities.artist import Artist
from letras.infrastructure.web.scraper import ScrapeResult
from letras.runners.incremental import IncrementalRunner


class TestIncrementalRunner:
    @pytest.fixture
    async def mock_repository(self):
        repo = MagicMock()
        repo.get_all_artists = AsyncMock()
        repo.update_artist_views = AsyncMock()
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
        runner = IncrementalRunner(
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
    async def test_process_new_artists(
        self, runner, mock_repository, mock_scraper, mock_service
    ):
        # Setup
        existing = [Artist(name="Existing", slug="existing", id=1, views=1000)]
        new = [Artist(name="New", slug="new")]
        processed = Artist(name="New", slug="new", id=2, views=1000)

        mock_repository.get_all_artists.return_value = existing
        mock_scraper.get_all_artists.return_value = existing + new
        mock_service.process_artist.return_value = processed
        mock_scraper.get_artist_details.return_value = ScrapeResult(
            content="", views=1000
        )

        # Execute
        result = await runner.process_artists()

        # Verify
        assert len(result) == 2
        assert any(a.slug == "new" for a in result)
        assert mock_service.process_artist.await_count >= 1

    @pytest.mark.asyncio
    async def test_update_existing_artists(self, runner, mock_repository, mock_scraper):
        # Setup
        existing = Artist(name="Test", slug="test", id=1, views=1000)

        mock_repository.get_all_artists.return_value = [existing]
        mock_scraper.get_all_artists.return_value = [existing]
        mock_scraper.get_artist_details.return_value = ScrapeResult(
            content="", views=2000
        )

        # Execute
        result = await runner.process_artists()

        # Verify
        assert len(result) == 1
        assert result[0].views == 2000
        mock_repository.update_artist_views.assert_awaited_once_with(1, 2000)

    @pytest.mark.asyncio
    async def test_no_updates_needed(self, runner, mock_repository, mock_scraper):
        # Setup
        existing = Artist(name="Test", slug="test", id=1, views=1000)

        mock_repository.get_all_artists.return_value = [existing]
        mock_scraper.get_all_artists.return_value = [existing]
        mock_scraper.get_artist_details.return_value = ScrapeResult(
            content="", views=1000
        )

        # Execute
        result = await runner.process_artists()

        # Verify
        assert len(result) == 1
        assert result[0].views == 1000
        assert not mock_repository.update_artist_views.called

    @pytest.mark.asyncio
    async def test_error_handling(self, runner, mock_repository):
        # Setup
        mock_repository.get_all_artists.side_effect = Exception("Test error")

        # Execute & Verify
        with pytest.raises(Exception) as exc:
            await runner.process_artists()

        assert "Test error" in str(exc.value)
