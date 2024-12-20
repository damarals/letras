from typing import List

from letras.domain.entities.artist import Artist
from letras.domain.services.language_service import LanguageService
from letras.domain.services.lyrics_service import LyricsService
from letras.infrastructure.database.connection import PostgresConnection
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)
from letras.infrastructure.web.scraper import WebScraper

from .base import BaseRunner


class FullRunner(BaseRunner):
    """Full scraping of all artists"""

    async def initialize(self):
        """Initialize resources for the runner."""
        self.db = PostgresConnection(**self.db_config)
        await self.db.initialize()
        self.repository = PostgresRepository(self.db)
        self.scraper = WebScraper(self.base_url)
        await self.scraper.initialize()
        self.language_service = LanguageService()
        self.service = LyricsService(
            repository=self.repository,
            language_service=self.language_service,
            scraper=self.scraper,
        )

    async def run(self, output_dir: str):
        """Execute the full scraping process."""
        artists = await self.process_artists()
        songs = await self.process_songs(artists)
        lyrics = await self.process_lyrics(artists, songs)
        await self.create_release(lyrics, output_dir, temp_dir=f"{output_dir}/temp")

    async def process_artists(self) -> List[Artist]:
        """Process all artists"""
        self.console.print("[blue]Starting full scrape...[/blue]")

        try:
            web_artists = await self.scraper.get_all_artists()
            if not web_artists:
                return []

            processed = []
            for artist in web_artists:
                try:
                    processed_artist = await self.service.process_artist(artist)
                    if processed_artist:
                        processed.append(processed_artist)
                        if self.verbose:
                            self.console.print(f"[blue]Processed[/blue] {artist.name}")
                except Exception as e:
                    self.console.print(f"[red]Error[/red] with {artist.name}: {str(e)}")

            return processed

        except Exception as e:
            self.console.print("[red]Error[/red] getting artists:", str(e))
            raise
