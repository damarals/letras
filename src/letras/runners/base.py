import asyncio
import shutil
import string
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.domain.services.lyrics_service import LyricsService
from letras.infrastructure.database.connection import PostgresConnection
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)
from letras.infrastructure.database.utils import PostgresUtils
from letras.infrastructure.web.scraper import WebScraper


class BaseRunner(ABC):
    def __init__(self, db_config: dict, base_url: str, verbose: bool = True):
        self.verbose = verbose
        self.console = Console()
        self.db_config = db_config
        self.base_url = base_url

        # Services will be initialized later
        self.db = None
        self.repository = None
        self.scraper = None
        self.language_service = None
        self.service = None

    @abstractmethod
    async def process_artists(self) -> List[Artist]:
        """Process artists based on runner strategy"""
        pass

    @abstractmethod
    async def initialize(self):
        """Initialize resources for the runner"""
        pass

    @abstractmethod
    async def run(self, output_dir: str):
        """Execute the runner logic"""
        pass

    async def close(self):
        """Close resources"""
        if self.db:
            await self.db.close()
        if self.scraper:
            await self.scraper.close()

    def group_artists(self, artists: List[Artist]) -> Dict[str, List[Artist]]:
        """Group artists by their first character"""
        groups = defaultdict(list)

        for artist in artists:
            # Get first character of artist name
            first_char = artist.name[0].upper()

            # Group into: numbers, letters, or 'other'
            if first_char.isdigit():
                group_key = "#"
            elif first_char in string.ascii_uppercase:
                group_key = first_char
            else:
                group_key = "Other"

            groups[group_key].append(artist)

        return dict(sorted(groups.items()))

    @abstractmethod
    async def process_artists(self) -> List[Artist]:
        """Process artists based on runner strategy"""
        pass

    async def process_songs(self, artists: List[Artist]) -> List[Song]:
        """Process songs with clean progress display"""
        new_songs = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            # Group artists
            grouped_artists = self.group_artists(artists)
            main_task = progress.add_task(
                "[yellow]Processing songs...", total=len(grouped_artists)
            )

            for group_key, group_artists in grouped_artists.items():
                group_task = progress.add_task(
                    f"[cyan]Songs from group {group_key}", total=len(group_artists)
                )

                songs_in_group = 0
                for artist in group_artists:
                    try:
                        songs = await self.service.process_songs(artist)
                        songs_in_group += len(songs)
                        new_songs.extend(songs)
                    except Exception as e:
                        if self.verbose:
                            progress.print(f"[red]Error in group {group_key}[/red]")
                    finally:
                        progress.advance(group_task)

                progress.print(f"Group {group_key}: {songs_in_group} new songs found")
                progress.advance(main_task)

        return new_songs

    async def process_lyrics(
        self, artists: List[Artist], songs: List[Song]
    ) -> List[Lyrics]:
        """Process lyrics concurrently"""
        lyrics_list = []
        artist_map = {artist.id: artist for artist in artists}

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("[blue]Processing lyrics...", total=len(songs))

            async def process_song_lyrics(song: Song):
                try:
                    artist = artist_map[song.artist_id]
                    lyrics = await self.service.process_lyrics(artist, song)
                    if lyrics and self.verbose:
                        self.console.print(f"Added lyrics for {song.name}")
                    return lyrics
                except Exception as e:
                    self.console.print(
                        f"[red]Error[/red] processing {song.name}: {str(e)}"
                    )
                    return None
                finally:
                    progress.advance(task)

            tasks = [process_song_lyrics(song) for song in songs]
            results = await asyncio.gather(*tasks)
            lyrics_list = [l for l in results if l]

        return lyrics_list

    async def create_release(
        self, lyrics_list: List[Lyrics], output_dir: str, temp_dir: str
    ):
        """Create release files"""
        if not lyrics_list:
            return

        try:
            # Create lyrics files
            for lyrics in lyrics_list:
                song = await self.repository.get_song_by_id(lyrics.song_id)
                artist = await self.repository.get_artist_by_id(song.artist_id)

                filename = f"{artist.name} - {song.name}.txt".replace("/", "_")
                with open(f"{temp_dir}/{filename}", "w") as f:
                    f.write(f"{song.name}\n{artist.name}\n\n{lyrics.content}")

            # Create database backup
            postgres_utils = PostgresUtils(self.db_config)
            backup_file = await postgres_utils.create_backup(temp_dir)

            # Create zip including both lyrics and database backup
            timestamp = datetime.now().strftime("%Y%m%d")
            shutil.make_archive(f"{output_dir}/letras-{timestamp}", "zip", temp_dir)

            # Create release notes
            await self._create_notes(lyrics_list, output_dir)

            # Cleanup
            shutil.rmtree(temp_dir)

        except Exception as e:
            self.console.print(f"[red]Error[/red] creating release: {str(e)}")
            raise

    async def _create_notes(self, lyrics_list: List[Lyrics], output_dir: str):
        """Create markdown release notes"""
        stats = {}
        for lyrics in lyrics_list:
            song = await self.repository.get_song_by_id(lyrics.song_id)
            artist = await self.repository.get_artist_by_id(song.artist_id)

            if artist.id not in stats:
                stats[artist.id] = {
                    "name": artist.name,
                    "songs": 0,
                    "views": artist.views,
                }
            stats[artist.id]["songs"] += 1

        content = f"""# Letras Gospel Update\n
Added {len(lyrics_list)} new songs from {len(stats)} artists.\n
## Top Artists\n"""

        for artist in sorted(stats.values(), key=lambda x: x["views"], reverse=True)[
            :5
        ]:
            content += f"- **{artist['name']}** ({artist['songs']} songs)\n"

        with open(f"{output_dir}/RELEASE_NOTES.md", "w") as f:
            f.write(content)
