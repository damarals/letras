from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientError, ClientSession, ClientTimeout

from letras.domain.entities.artist import Artist
from letras.domain.entities.song import Song
from letras.infrastructure.web.scraper import ScrapeResult, WebScraper


class TestWebScraper:
    @pytest.fixture
    async def scraper(self):
        scraper = WebScraper(base_url="https://test.com")
        await scraper.initialize()
        yield scraper
        await scraper.close()

    @pytest.mark.asyncio
    async def test_artist_list_parsing(self, scraper, sample_html):
        with patch.object(scraper, "_get") as mock_get:
            mock_get.return_value = sample_html["artist_list"]

            artists = await scraper.get_all_artists()
            assert len(artists) == 2
            assert all(isinstance(a, Artist) for a in artists)
            assert artists[0].name == "Artist 1"
            assert artists[0].slug == "artist1"

    @pytest.mark.asyncio
    async def test_artist_details_parsing(self, scraper, sample_html):
        with patch.object(scraper, "_get") as mock_get:
            mock_get.return_value = sample_html["artist_page"]
            artist = Artist(name="Test", slug="test")

            result = await scraper.get_artist_details(artist)
            assert isinstance(result, ScrapeResult)
            assert result.views == 1234

    @pytest.mark.asyncio
    async def test_song_list_parsing(self, scraper, sample_html):
        with patch.object(scraper, "_get") as mock_get:
            mock_get.return_value = sample_html["artist_page"]
            artist = Artist(name="Test", slug="test", id=1)

            songs = await scraper.get_artist_songs(artist)
            assert len(songs) == 1
            assert isinstance(songs[0], Song)
            assert songs[0].name == "Song 1"
            assert songs[0].artist_id == artist.id

    @pytest.mark.asyncio
    async def test_song_details_parsing(self, scraper, sample_html):
        with patch.object(scraper, "_get") as mock_get:
            mock_get.return_value = sample_html["song_page"]
            artist = Artist(name="Test", slug="test")
            song = Song(name="Test", slug="test", artist_id=1)

            result = await scraper.get_song_details(artist, song)
            assert isinstance(result, ScrapeResult)
            assert result.views == 500
            assert "Verse 1" in result.content
            assert "Verse 2" in result.content

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, scraper):
        # Mock the session get method directly
        mock_response = MagicMock()
        mock_response.text = AsyncMock(return_value="success")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(scraper._session, "get") as mock_get:
            # First two attempts fail, third succeeds
            mock_get.side_effect = [
                ClientError(),  # First attempt
                ClientError(),  # Second attempt
                mock_response,  # Third attempt succeeds
            ]

            result = await scraper._get("/test")
            assert result == "success"
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        with patch.object(scraper._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = AsyncMock(return_value="success")
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()
            mock_get.return_value = mock_response

            # Make multiple concurrent requests
            import asyncio

            tasks = [scraper._get("/test") for _ in range(5)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 5
            assert all(r == "success" for r in results)
            assert mock_get.call_count == 5

    @pytest.mark.asyncio
    async def test_error_handling(self, scraper):
        with patch.object(scraper._session, "get") as mock_get:
            mock_get.side_effect = ClientError()

            artist = Artist(name="Test", slug="test")
            result = await scraper.get_artist_details(artist)
            assert result is None
