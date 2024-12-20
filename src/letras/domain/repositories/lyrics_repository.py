from abc import ABC, abstractmethod
from typing import List, Optional

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song


class LyricsRepository(ABC):
    @abstractmethod
    async def get_all_artists(self) -> List[Artist]:
        """Get all artists"""
        pass

    @abstractmethod
    async def get_artist_by_slug(self, slug: str) -> Optional[Artist]:
        """Get artist by slug"""
        pass

    @abstractmethod
    async def get_artist_by_id(self, artist_id: int) -> Optional[Artist]:
        """Get artist by ID"""
        pass

    @abstractmethod
    async def add_artist(self, artist: Artist) -> Artist:
        """Add new artist"""
        pass

    @abstractmethod
    async def update_artist_views(self, artist_id: int, views: int) -> None:
        """Update artist views"""
        pass

    @abstractmethod
    async def get_songs_by_artist(self, artist_id: int) -> List[Song]:
        """Get all songs from artist"""
        pass

    @abstractmethod
    async def get_song_by_id(self, song_id: int) -> Optional[Song]:
        """Get song by ID"""
        pass

    @abstractmethod
    async def add_song(self, song: Song) -> Song:
        """Add new song"""
        pass

    @abstractmethod
    async def add_lyrics(self, lyrics: Lyrics) -> Lyrics:
        """Add lyrics"""
        pass

    @abstractmethod
    async def get_lyrics_by_song(self, song_id: int) -> Optional[Lyrics]:
        """Get lyrics by song ID"""
        pass
