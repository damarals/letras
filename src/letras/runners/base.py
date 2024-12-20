import asyncio
import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.domain.services.lyrics_service import LyricsService
from letras.infrastructure.database.connection import PostgresConnection
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)
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

    @abstractmethod
    async def process_artists(self) -> List[Artist]:
        """Process artists based on runner strategy"""
        pass

    async def process_songs(self, artists: List[Artist]) -> List[Song]:
        """Process songs from artists concurrently"""
        new_songs = []

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("[blue]Processing songs...", total=len(artists))

            async def process_artist_songs(artist: Artist):
                try:
                    songs = await self.service.process_songs(artist)
                    if songs and self.verbose:
                        self.console.print(
                            f"Found {len(songs)} new songs from {artist.name}"
                        )
                    return songs
                except Exception as e:
                    self.console.print(
                        f"[red]Error[/red] processing {artist.name}: {str(e)}"
                    )
                    return []
                finally:
                    progress.advance(task)

            tasks = [process_artist_songs(artist) for artist in artists]
            results = await asyncio.gather(*tasks)
            for songs in results:
                new_songs.extend(songs)

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

            # Create zip
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
