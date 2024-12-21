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


class IncrementalRunner(BaseRunner):
    """Incremental update of existing database"""

    async def initialize(self):
        """Initialize resources and restore database if backup exists"""
        self.db = PostgresConnection(**self.db_config)
        await self.db.initialize()

        # Look for latest backup in the release directory
        release_dir = Path(self.config.release_dir)
        backup_files = list(release_dir.glob("*.sql"))

        if backup_files:
            # Get most recent backup
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)

            # Restore backup
            postgres_utils = PostgresUtils(self.db_config)
            await postgres_utils.restore_backup(str(latest_backup))

            if self.verbose:
                self.console.print(
                    f"[green]Restored database from backup: {latest_backup}[/green]"
                )

        # Initialize remaining services
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
        """Process new and update existing artists with grouped progress"""
        self.console.print("[blue]Starting incremental update...[/blue]")

        try:
            # Get existing and web artists
            existing = await self.repository.get_all_artists()
            existing_slugs = {a.slug for a in existing}

            web_artists = await self.scraper.get_all_artists()
            if not web_artists:
                return []

            # Find new artists
            new_artists = [a for a in web_artists if a.slug not in existing_slugs]

            # Process artists with grouped progress
            processed = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
            ) as progress:
                # Process new artists
                if new_artists:
                    grouped_new = self.group_artists(new_artists)
                    new_task = progress.add_task(
                        "[yellow]Processing new artists...", total=len(grouped_new)
                    )

                    for group_key, artists in grouped_new.items():
                        group_task = progress.add_task(
                            f"[cyan]New artists in group {group_key}",
                            total=len(artists),
                        )

                        processed_in_group = 0
                        for artist in artists:
                            try:
                                if processed_artist := await self.service.process_artist(
                                    artist
                                ):
                                    processed.append(processed_artist)
                                    processed_in_group += 1
                            except Exception as e:
                                if self.verbose:
                                    progress.print(
                                        f"[red]Error in group {group_key}[/red]"
                                    )
                            finally:
                                progress.advance(group_task)

                        progress.print(
                            f"Group {group_key}: {processed_in_group} new artists added"
                        )
                        progress.advance(new_task)

                # Update existing artists
                grouped_existing = self.group_artists(existing)
                update_task = progress.add_task(
                    "[yellow]Updating existing artists...", total=len(grouped_existing)
                )

                for group_key, artists in grouped_existing.items():
                    group_task = progress.add_task(
                        f"[cyan]Updating group {group_key}", total=len(artists)
                    )

                    updates_in_group = 0
                    for artist in artists:
                        try:
                            result = await self.scraper.get_artist_details(artist)
                            if result and result.views != artist.views:
                                await self.repository.update_artist_views(
                                    artist.id, result.views
                                )
                                artist.views = result.views
                                updates_in_group += 1
                            processed.append(artist)
                        except Exception as e:
                            if self.verbose:
                                progress.print(
                                    f"[red]Error updating in group {group_key}[/red]"
                                )
                            processed.append(artist)
                        finally:
                            progress.advance(group_task)

                    progress.print(
                        f"Group {group_key}: {updates_in_group} artists updated"
                    )
                    progress.advance(update_task)

            return processed

        except Exception as e:
            self.console.print("[red]Error[/red] during update:", str(e))
            raise
