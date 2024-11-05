import pytest
from unittest.mock import patch, mock_open

from core.filters import LyricsFilter

@pytest.fixture
def mock_config():
    return """
filters:
  artists:
    exclude_keywords:
      - Padre
      - Frei
  titles:
    exclude_keywords:
      - Ave Maria
      - Terço
  lyrics:
    language: pt
    min_length: 100
    max_length: 4000
"""

@pytest.fixture
def lyrics_filter(mock_config):
    with patch('builtins.open', mock_open(read_data=mock_config)):
        return LyricsFilter()

def test_should_include_artist(lyrics_filter):
    """Test artist filtering"""
    assert lyrics_filter.should_include_artist("Valid Artist")
    assert not lyrics_filter.should_include_artist("Padre João")

def test_should_include_title(lyrics_filter):
    """Test title filtering"""
    assert lyrics_filter.should_include_title("Valid Song")
    assert not lyrics_filter.should_include_title("Ave Maria da Graça")

def test_should_include_lyrics(lyrics_filter):
    """Test lyrics filtering"""
    with patch('core.utils.LanguageDetector.is_portuguese', return_value=True):
        valid_lyrics = "A" * 200  # Valid length
        assert lyrics_filter.should_include_lyrics(valid_lyrics)
        
        short_lyrics = "A" * 50  # Too short
        assert not lyrics_filter.should_include_lyrics(short_lyrics)