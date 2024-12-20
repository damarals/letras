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


class IncrementalRunner(BaseRunner):
    """Incremental update of existing database"""

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
        """Execute the incremental scraping process."""
        artists = await self.process_artists()
        songs = await self.process_songs(artists)
        lyrics = await self.process_lyrics(artists, songs)
        await self.create_release(lyrics, output_dir, temp_dir=f"{output_dir}/temp")

    async def process_artists(self) -> List[Artist]:
        """Process new artists and update existing"""
        self.console.print("[blue]Starting incremental update...[/blue]")

        try:
            # Get existing and web artists
            existing = await self.repository.get_all_artists()
            existing_slugs = {a.slug for a in existing}

            web_artists = await self.scraper.get_all_artists()
            if not web_artists:
                return existing

            processed = []

            # Process new artists
            new_artists = [a for a in web_artists if a.slug not in existing_slugs]
            for artist in new_artists:
                try:
                    if processed_artist := await self.service.process_artist(artist):
                        processed.append(processed_artist)
                        if self.verbose:
                            self.console.print(f"[blue]Added[/blue] {artist.name}")
                except Exception as e:
                    self.console.print(
                        f"[red]Error[/red] adding {artist.name}: {str(e)}"
                    )

            # Update existing artists
            for artist in existing:
                try:
                    result = await self.scraper.get_artist_details(artist)
                    if result and result.views != artist.views:
                        await self.repository.update_artist_views(
                            artist.id, result.views
                        )
                        artist.views = result.views
                        if self.verbose:
                            self.console.print(f"[blue]Updated[/blue] {artist.name}")
                    processed.append(artist)
                except Exception as e:
                    self.console.print(
                        f"[red]Error[/red] updating {artist.name}: {str(e)}"
                    )
                    processed.append(artist)

            return processed

        except Exception as e:
            self.console.print("[red]Error[/red] during update:", str(e))
            raise
