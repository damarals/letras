import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

pytestmark = pytest.mark.asyncio(scope="function")


@pytest.fixture
async def db_config() -> dict:
    """Test database config"""
    return {
        "host": "db",  # Use docker service name
        "port": 5432,
        "database": "letras",
        "user": "letras",
        "password": "letras",
    }


@pytest.fixture
async def mock_connection():
    """Mock database connection for unit tests"""
    conn = MagicMock()
    conn.transaction = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
async def mock_repository(mock_connection):
    """Mock repository for unit tests"""
    repo = Mock()
    repo.get_artist_by_slug = AsyncMock(return_value=None)
    repo.add_artist = AsyncMock()
    repo.get_all_artists = AsyncMock(return_value=[])
    repo.get_songs_by_artist = AsyncMock(return_value=[])
    repo._conn = mock_connection
    return repo


@pytest.fixture
def mock_scraper():
    """Mock scraper for unit tests"""
    scraper = Mock()
    scraper.get_all_artists = AsyncMock(return_value=[])
    scraper.get_artist_details = AsyncMock(return_value=None)
    scraper.get_artist_songs = AsyncMock(return_value=[])
    scraper.get_song_details = AsyncMock(return_value=None)
    return scraper


@pytest.fixture
def mock_language_service():
    """Mock language service for unit tests"""
    service = Mock()
    service.is_portuguese = Mock(return_value=True)
    return service


@pytest.fixture
async def lyrics_service(mock_repository, mock_language_service, mock_scraper):
    """Test lyrics service"""
    return LyricsService(
        repository=mock_repository,
        language_service=mock_language_service,
        scraper=mock_scraper,
    )


@pytest.fixture
def temp_path() -> Generator[Path, None, None]:
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir)
        yield path


@pytest.fixture(autouse=True)
def clean_temp_files(temp_path):
    """Cleanup temp files after each test"""
    yield
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_html() -> dict:
    """Sample HTML responses"""
    return {
        "artist_list": """
            <div class="artist-list">
                <a href="/artist1/">Artist 1</a>
                <a href="/artist2/">Artist 2</a>
            </div>
        """,
        "artist_page": """
            <div class="head-info-exib">
                <b>1234</b>
            </div>
            <div class="songList-table">
                <li class="songList-table-row">
                    <a class="songList-table-songName" href="/song1">Song 1</a>
                </li>
            </div>
        """,
        "song_page": """
            <div class="head-info-exib">
                <b>500</b>
            </div>
            <div class="lyric-original">
                <p>Verse 1</p>
                <p>Verse 2</p>
            </div>
        """,
    }
