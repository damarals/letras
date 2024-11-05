import yaml
from pathlib import Path
from typing import Dict, Any

from core.utils import LanguageDetector

class LyricsFilter:
    """
    Class to handle filtering of artists, song titles, and lyrics content
    based on configured rules.
    """
    
    def __init__(self, config_path: str = "configs/filters.yaml"):
        """
        Initialize the filter with configuration from YAML file.
        
        Parameters:
        -----------
        config_path : str
            Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.language_detector = LanguageDetector()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def should_include_artist(self, artist_name: str) -> bool:
        """
        Check if an artist should be included based on exclusion keywords.
        
        Parameters:
        -----------
        artist_name : str
            Name of the artist to check
        
        Returns:
        --------
        bool
            True if artist should be included (no exclusion keywords found),
            False if artist should be excluded
        """
        artist_name = artist_name.lower()
        exclude_keywords = [k.lower() for k in self.config['filters']['artists']['exclude_keywords']]
        
        # Return False if any exclusion keyword is found in the artist name
        return not any(keyword in artist_name for keyword in exclude_keywords)
    
    def should_include_title(self, title: str) -> bool:
        """
        Check if a song title should be included based on exclusion keywords.
        
        Parameters:
        -----------
        title : str
            Title of the song to check
        
        Returns:
        --------
        bool
            True if title should be included (no exclusion keywords found),
            False if title should be excluded
        """
        title = title.lower()
        exclude_keywords = [k.lower() for k in self.config['filters']['titles']['exclude_keywords']]
        
        # Return False if any exclusion keyword is found in the title
        return not any(keyword in title for keyword in exclude_keywords)
    
    def should_include_lyrics(self, lyrics: str) -> bool:
        """
        Check if lyrics should be included based on language and content rules.
        
        Parameters:
        -----------
        lyrics : str
            The lyrics content to check
        
        Returns:
        --------
        bool
            True if lyrics should be included, False otherwise
        """
        lyrics_config = self.config['filters']['lyrics']
        
        # Check length constraints
        if not (lyrics_config['min_length'] <= len(lyrics) <= lyrics_config['max_length']):
            return False
        
        # Check language
        if not self.language_detector.is_portuguese(lyrics):
            return False
        
        # Check title patterns in lyrics
        return self.should_include_title(lyrics)