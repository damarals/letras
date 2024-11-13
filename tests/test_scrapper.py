from unittest.mock import patch
import pytest
from bs4 import BeautifulSoup

from core.scrapper import extract_song_views, get_artists, get_artist_songs, get_artist_song_lyrics, extract_artist_views

@pytest.fixture
def mock_html_responses():
    """Mock HTML responses for different endpoints"""
    return {
        'artists': """
            <div class="artista-todas">
                <a href="/artist1/">Artist 1</a>
                <a href="/artist2/">Artist 2</a>
            </div>
        """,
        'songs': """
            <div class="artista-todas">
                <ul class="songList-table-content">
                    <li class="songList-table-row">
                        <a class="songList-table-songName" href="/artist1/song1/">Song 1</a>
                    </li>
                </ul>
            </div>
        """,
        'lyrics': """
            <div class="head-info-exib">
                <b>1.234</b>
            </div>
            <div class="lyric-original">
                <p>Verse 1</p>
                <p>Verse 2</p>
            </div>
        """
    }

def test_get_artists(mock_html_responses):
    """Test artist scraping"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = mock_html_responses['artists']
        
        df = get_artists()
        assert not df.is_empty()
        assert 'name' in df.columns
        assert 'slug' in df.columns

def test_get_artist_songs(mock_html_responses):
    """Test song scraping"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = mock_html_responses['songs']
        
        df = get_artist_songs('artist1')
        assert not df.is_empty()
        assert 'name' in df.columns
        assert 'slug' in df.columns

def test_get_artist_song_lyrics(mock_html_responses):
    """Test lyrics scraping"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = mock_html_responses['lyrics']
        
        lyrics, views = get_artist_song_lyrics('artist1', 'song1')
        assert lyrics is not None
        assert 'Verse 1' in lyrics
        assert 'Verse 2' in lyrics
        assert views == 1234

def test_extract_artist_views():
    """Test view count extraction"""
    html = """
        <div class="head-info-exib">
            <b>1.234</b>
        </div>
    """
    soup = BeautifulSoup(html, 'html.parser')
    views = extract_artist_views(soup)
    assert views == 1234

def test_extract_song_views():
    """Test song view count extraction"""
    html = """
        <div class="head-info-exib">
            <b>5.678</b>
        </div>
    """
    soup = BeautifulSoup(html, 'html.parser')
    views = extract_song_views(soup)
    assert views == 5678