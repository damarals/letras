from typing import List, Optional

from rich.console import Console

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.domain.repositories.lyrics_repository import LyricsRepository
from letras.infrastructure.web.scraper import WebScraper

from .language_service import LanguageService


class LyricsService:
    def __init__(
        self,
        repository: LyricsRepository,
        language_service: LanguageService,
        scraper: WebScraper,
    ):
        self.repository = repository
        self.language_service = language_service
        self.scraper = scraper
        self.console = Console()

    async def process_artist(self, artist: Artist) -> Artist:
        """Process an artist"""
        try:
            scrape_result = await self.scraper.get_artist_details(artist)
            if not scrape_result:
                return None

            artist.views = scrape_result.views
            existing = await self.repository.get_artist_by_slug(artist.slug)

            if existing:
                if existing.views != artist.views:
                    await self.repository.update_artist_views(existing.id, artist.views)
                return existing

            return await self.repository.add_artist(artist)

        except Exception as e:
            self.console.print(
                f"[red]Error[/red] processing artist {artist.name}: {str(e)}"
            )
            raise

    async def process_songs(self, artist: Artist) -> List[Song]:
        """Process artist songs"""
        try:
            web_songs = await self.scraper.get_artist_songs(artist)
            if not web_songs:
                return []

            existing = {
                s.slug: s for s in await self.repository.get_songs_by_artist(artist.id)
            }

            return [s for s in web_songs if s.slug not in existing]

        except Exception as e:
            self.console.print(
                f"[red]Error[/red] processing songs for {artist.name}: {str(e)}"
            )
            raise

    async def process_lyrics(self, artist: Artist, song: Song) -> Optional[Lyrics]:
        """Process song lyrics"""
        try:
            if song.id:
                existing = await self.repository.get_lyrics_by_song(song.id)
                if existing:
                    return existing

            scrape_result = await self.scraper.get_song_details(artist, song)
            if not scrape_result:
                return None

            song.views = scrape_result.views

            if not self.language_service.is_portuguese(scrape_result.content):
                return None

            if not song.id:
                song = await self.repository.add_song(song)

            lyrics = Lyrics(song_id=song.id, content=scrape_result.content)
            return await self.repository.add_lyrics(lyrics)

        except Exception as e:
            self.console.print(
                f"[red]Error[/red] processing lyrics for {song.name}: {str(e)}"
            )
            raise
