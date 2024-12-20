import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from bs4 import BeautifulSoup

from letras.domain.entities.artist import Artist
from letras.domain.entities.song import Song
from letras.infrastructure.web.scraper import ScrapeResult, WebScraper


class MockResponse:
    def __init__(self, text_data):
        self._text = text_data

    async def text(self):
        return self._text

    def raise_for_status(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.get = MagicMock(return_value=MockResponse("mock response"))
    session.close = AsyncMock()
    return session


@pytest.fixture
async def scraper(mock_session):
    with patch("aiohttp.ClientSession", return_value=mock_session):
        scraper = WebScraper(base_url="https://www.letras.mus.br")
        await scraper.initialize()
        yield scraper
        await scraper.close()


@pytest.mark.asyncio
async def test_get_all_artists(scraper, mock_session):
    mock_html = """
        <div class="artist-list">
            <a href="/artist1/">Artist 1</a>
            <a href="/artist2/">Artist 2</a>
        </div>
    """
    mock_session.get = MagicMock(return_value=MockResponse(mock_html))

    artists = await scraper.get_all_artists()

    assert len(artists) == 2
    assert all(isinstance(a, Artist) for a in artists)
    assert artists[0].name == "Artist 1"
    assert artists[0].slug == "artist1"


@pytest.mark.asyncio
async def test_get_artist_details(scraper, mock_session):
    mock_html = """
        <div class="head-info-exib">
            <b>1234</b>
        </div>
    """
    mock_session.get = MagicMock(return_value=MockResponse(mock_html))

    artist = Artist(name="Test", slug="test")
    result = await scraper.get_artist_details(artist)

    assert isinstance(result, ScrapeResult)
    assert result.views == 1234


@pytest.mark.asyncio
async def test_get_artist_songs(scraper, mock_session):
    mock_html = """
        <div class="songList-table">
            <li class="songList-table-row">
                <a class="songList-table-songName" href="/song1" title="Song 1">Song 1</a>
            </li>
        </div>
    """
    mock_session.get = MagicMock(return_value=MockResponse(mock_html))

    artist = Artist(name="Test", slug="test", id=1)
    songs = await scraper.get_artist_songs(artist)

    assert len(songs) == 1
    assert isinstance(songs[0], Song)
    assert songs[0].name == "Song 1"
    assert songs[0].artist_id == artist.id


@pytest.mark.asyncio
async def test_get_song_details(scraper, mock_session):
    mock_html = """
        <div class="head-info-exib">
            <b>500</b>
        </div>
        <div class="lyric-original">
            <p>Verse 1</p>
            <p>Verse 2</p>
        </div>
    """
    mock_session.get = MagicMock(return_value=MockResponse(mock_html))

    artist = Artist(name="Test", slug="test")
    song = Song(name="Test Song", slug="test-song", artist_id=1)
    result = await scraper.get_song_details(artist, song)

    assert isinstance(result, ScrapeResult)
    assert result.views == 500
    assert "Verse 1" in result.content
    assert "Verse 2" in result.content


@pytest.mark.asyncio
async def test_rate_limiting(scraper, mock_session):
    mock_session.get = MagicMock(return_value=MockResponse("OK"))

    tasks = []
    for _ in range(20):
        tasks.append(scraper._get("/test"))

    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    assert all(r == "OK" for r in results)


@pytest.mark.asyncio
async def test_error_handling(scraper, mock_session):
    error_response = MockResponse("")
    error_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientError())
    mock_session.get = MagicMock(return_value=error_response)

    artist = Artist(name="Test", slug="test")
    result = await scraper.get_artist_details(artist)

    assert result is None
