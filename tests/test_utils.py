from unittest.mock import patch
from lingua import Language
import pytest

from core.utils import load_config, sanitize_filename, setup_database, LanguageDetector

def test_sanitize_filename():
    """Test filename sanitization"""
    test_cases = [
        ("test/file.txt", "testfile.txt"),
        ("test:file*.txt", "testfile.txt"),
        ("test   file.txt", "test file.txt"),
        ("áéíóú.txt", "aeiou.txt")
    ]
    
    for input_name, expected in test_cases:
        assert sanitize_filename(input_name) == expected

def test_load_config(mock_config_file):
    """Test configuration loading"""
    with patch('core.utils.Path') as mock_path:
        mock_path.return_value = mock_config_file
        config = load_config()
        
        assert config.base_url == 'https://mock.url'

def test_language_detector():
    """Test language detection"""
    detector = LanguageDetector()
    
    detector.return_value = Language.PORTUGUESE
    assert detector.is_portuguese("Texto em português")
        
    detector.return_value = Language.ENGLISH
    assert not detector.is_portuguese("English text")

def test_setup_database(tmp_path):
    """Test database setup"""
    db_path = tmp_path / "test.duckdb"
    conn = setup_database(db_path)
    
    # Verify tables were created
    tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """).fetchall()
    
    table_names = {t[0] for t in tables}
    assert 'artists' in table_names
    assert 'songs' in table_names
    assert 'lyrics' in table_names
    
    conn.close()