import re
import unicodedata
import duckdb
from lingua import Language, LanguageDetectorBuilder
from pathlib import Path
from box import Box
from dotenv import load_dotenv
from rich.console import Console
import yaml

def load_config() -> Box:
    """
    Load configuration from YAML file.

    Returns
    -------
    config: Box
        Box object containing configuration.
    """
    config_path = Path("configs/config.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return Box(config)

def setup_database(db_path: Path) -> duckdb.DuckDBPyConnection:
    """
    Setup database connection and create tables if they don't exist
    
    Parameters:
    -----------
    db_path : Path
        Path to the database file
    
    Returns:
    --------
    duckdb.DuckDBPyConnection
        Database connection
    """
    conn = duckdb.connect(str(db_path))
    
    # Create sequences
    conn.execute("CREATE SEQUENCE IF NOT EXISTS artists_id_seq START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS songs_id_seq START 1")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS lyrics_id_seq START 1")
    
    # Create tables with updated schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY DEFAULT nextval('artists_id_seq'),
            name VARCHAR,
            slug VARCHAR UNIQUE,
            views INTEGER DEFAULT 0
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY DEFAULT nextval('songs_id_seq'),
            artist_id INTEGER,
            name VARCHAR,
            slug VARCHAR,
            views INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artist_id) REFERENCES artists(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lyrics (
            id INTEGER PRIMARY KEY DEFAULT nextval('lyrics_id_seq'),
            song_id INTEGER,
            content TEXT,
            last_updated TIMESTAMP,
            FOREIGN KEY (song_id) REFERENCES songs(id)
        )
    """)
    
    return conn

def sanitize_filename(filename: str) -> str:
    """
    Remove invalid characters and normalize filename
    
    Parameters:
    -----------
    filename : str
        Original filename
    
    Returns:
    --------
    str
        Sanitized filename
    """
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ASCII', 'ignore').decode('ASCII')
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace multiple spaces/dots with single ones
    filename = re.sub(r'\s+', ' ', filename)
    filename = re.sub(r'\.+', '.', filename)
    
    # Remove spaces near dots
    filename = re.sub(r'\s*\.\s*', '.', filename)
    
    # Remove leading/trailing spaces
    filename = filename.strip()
    
    return filename


class LanguageDetector:
    """
    A class to detect if text is in Portuguese using Lingua.
    """
    
    def __init__(self):
        """
        Initialize the LanguageDetector with Lingua.
        """
        self.console = Console()
        self.detector = LanguageDetectorBuilder.from_all_languages().build()
    
    def is_portuguese(self, text: str) -> bool:
        """
        Check if the given text is in Portuguese.
        
        Parameters:
        -----------
        text : str
            Text to be checked
        
        Returns:
        --------
        bool
            True if text is in Portuguese, False otherwise
        """
        try:
            # Remove newlines e espaços extras
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Detecta o idioma
            detected_language = self.detector.detect_language_of(text)
            
            # Retorna True se for português
            return detected_language == Language.PORTUGUESE
            
        except Exception as e:
            self.console.print(f"[bold red]ERROR[/bold red]    [white]Error detecting language: {str(e)}")
            return False