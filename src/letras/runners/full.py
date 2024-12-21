from typing import Dict, List

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

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
        """Process all artists with grouped progress display"""
        self.console.print("[blue]Starting full scrape...[/blue]")

        try:
            web_artists = await self.scraper.get_all_artists()
            if not web_artists:
                return []

            # Group artists
            grouped_artists = self.group_artists(web_artists)
            processed_artists = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
            ) as progress:
                main_task = progress.add_task(
                    "[yellow]Processing all artists...", total=len(grouped_artists)
                )

                for group_key, artists in grouped_artists.items():
                    group_task = progress.add_task(
                        f"[cyan]Group {group_key}", total=len(artists)
                    )

                    for artist in artists:
                        try:
                            processed = await self.service.process_artist(artist)
                            if processed:
                                processed_artists.append(processed)
                        except Exception as e:
                            if self.verbose:
                                progress.print(f"[red]Error in group {group_key}[/red]")
                        finally:
                            progress.advance(group_task)

                    progress.print(
                        f"Group {group_key}: {len(artists)} artists processed"
                    )
                    progress.advance(main_task)

            return processed_artists

        except Exception as e:
            self.console.print("[red]Error[/red] getting artists:", str(e))
            raise
