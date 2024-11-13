import shutil
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import polars as pl
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn
from threading import Lock

from core.scrapper import extract_artist_views, get_artists, get_artist_songs, get_artist_song_lyrics
from core.utils import load_config, setup_database, sanitize_filename
from core.filters import LyricsFilter

class GospelLyricsRunner:
    def __init__(self, verbose=1):
        """Initialize the runner with necessary paths and configurations"""
        self.console = Console()
        self.config = load_config()
        self.verbose = verbose
        
        # Setup paths
        self.data_dir = Path("data")
        self.temp_dir = self.data_dir / "temp"
        self.db_path = self.data_dir / "letras.duckdb"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Setup database connection
        self.conn = setup_database(self.db_path)
        
        # Setup filters
        self.filters = LyricsFilter()
        
        # Add locks for thread safety
        self.db_lock = Lock()
        self.file_lock = Lock()
    
    def collect_all_songs(self) -> pl.DataFrame:
        """
        Collects all artists and their songs and returns a unified DataFrame
        """
        self.console.print("[bold blue]INFO[/bold blue]     [white]Collecting artists...")
        artists_df = self.scrape_artists()
        
        # Filter artists
        artists_df = artists_df.filter(
            pl.col('name').map_elements(
                lambda x: self.filters.should_include_artist(x),
                return_dtype=pl.Boolean
            )
        )
        
        artists_df = artists_df.sort("name")
        
        # Get existing artists from database
        existing_slugs = set()
        stored_artists = {}
        result = self.conn.execute("SELECT id, slug, views FROM artists").fetchall()
        if result:
            existing_slugs = {row[1] for row in result}
            stored_artists = {row[1]: {"id": row[0], "views": row[2]} for row in result}
        
        # Update existing artists' views
        for slug in existing_slugs:
            try:
                views = self.get_artist_views(slug)
                if views > 0 and views != stored_artists[slug]["views"]:
                    self.conn.execute("""
                        UPDATE artists SET views = ? WHERE slug = ?
                    """, [views, slug])
                    stored_artists[slug]["views"] = views
            except Exception as e:
                self.console.print(f"[bold yellow]WARNING[/bold yellow]     Failed to update views for {slug}: {str(e)}")
        
        # Store new artists in database
        new_artists = artists_df.filter(~pl.col('slug').is_in(existing_slugs))
        if not new_artists.is_empty():
            for artist in new_artists.iter_rows(named=True):
                try:
                    views = self.get_artist_views(artist['slug'])
                    self.conn.execute("""
                        INSERT INTO artists (name, slug, views)
                        VALUES (?, ?, ?)
                    """, [artist['name'], artist['slug'], views])
                    
                    # Get the ID of the inserted artist
                    artist_id = self.conn.execute("""
                        SELECT id FROM artists WHERE slug = ?
                    """, [artist['slug']]).fetchone()[0]
                    
                    stored_artists[artist['slug']] = {"id": artist_id, "views": views}
                    
                except Exception as e:
                    self.console.print(f"[bold yellow]WARNING[/bold yellow]     Failed to insert {artist['name']}: {str(e)}")
        
        # Now collect songs for each artist
        total_artists = len(stored_artists)
        self.console.print(f"[bold blue]INFO[/bold blue]     [white]Collecting songs from {total_artists} artists...")
        
        all_songs = []
        with ThreadPoolExecutor(max_workers=28) as executor:
            future_to_artist = {}
            for artist_slug, artist_info in stored_artists.items():
                future = executor.submit(self.scrape_songs, artist_slug)
                future_to_artist[future] = {
                    'slug': artist_slug,
                    'id': artist_info['id'],
                    'views': artist_info['views']
                }
            
            for future in as_completed(future_to_artist):
                artist_info = future_to_artist[future]
                try:
                    songs_df = future.result()
                    if not songs_df.is_empty():
                        # Filter songs
                        songs_df = songs_df.filter(
                            pl.col('name').map_elements(
                                lambda x: self.filters.should_include_title(x),
                                return_dtype=pl.Boolean
                            )
                        )
                        
                        if not songs_df.is_empty():
                            # Get artist name from database
                            artist_name = self.conn.execute("""
                                SELECT name FROM artists WHERE id = ?
                            """, [artist_info['id']]).fetchone()[0]
                            
                            # Add artist information
                            songs_df = songs_df.with_columns([
                                pl.lit(artist_info['id']).alias('artist_id'),
                                pl.lit(artist_name).alias('artist_name'),
                                pl.lit(artist_info['slug']).alias('artist_slug'),
                                pl.lit(artist_info['views']).alias('artist_views')
                            ])
                            
                            # Check which songs are new
                            existing_songs = self.conn.execute("""
                                SELECT slug FROM songs WHERE artist_id = ?
                            """, [artist_info['id']]).fetchall()
                            
                            existing_slugs = {row[0] for row in existing_songs}
                            new_songs = songs_df.filter(~pl.col('slug').is_in(existing_slugs))
                            
                            if not new_songs.is_empty():
                                all_songs.append(new_songs)
                                if self.verbose == 1:
                                    self.console.print(
                                        f"[bold blue]INFO[/bold blue]     [white]Found {len(new_songs)} new songs from {artist_name}"
                                    )
                except Exception as e:
                    self.console.print(f"[bold red]ERROR[/bold red]    Failed to collect songs from {artist_info['slug']}: {str(e)}")
        
        if not all_songs:
            self.console.print("[bold blue]INFO[/bold blue]     [white]No new songs found")
            return pl.DataFrame()
        
        return pl.concat(all_songs).sort(["artist_name", "name"])
    
    def process_song(self, song_data) -> bool:
        """
        Process a single song, including scraping lyrics and storage
        """
        try:
            # Extract lyrics and views
            lyrics, views = self.scrape_lyrics(song_data['artist_slug'], song_data['slug'])
            if not lyrics:
                self.console.print(
                    f"[bold yellow]WARNING[/bold yellow]     [white]No lyrics found for '{song_data['name']}' by {song_data['artist_name']}"
                )
                return False
        
            # Apply lyrics filter
            if not self.filters.should_include_lyrics(lyrics):
                return False

            # Save text file
            with self.file_lock:
                self.save_lyrics_file(song_data['artist_name'], song_data['name'], lyrics)
            
            # Store in database
            with self.db_lock:
                # Insert song with views
                self.conn.execute("""
                    INSERT INTO songs (artist_id, name, slug, views)
                    SELECT ?, ?, ?, ?
                    WHERE NOT EXISTS (
                        SELECT 1 FROM songs 
                        WHERE artist_id = ? AND slug = ?
                    )
                """, [song_data['artist_id'], song_data['name'], song_data['slug'], views,
                    song_data['artist_id'], song_data['slug']])
                
                # Get song ID
                song_id = self.conn.execute(
                    "SELECT id FROM songs WHERE artist_id = ? AND slug = ?",
                    [song_data['artist_id'], song_data['slug']]
                ).fetchone()[0]
                
                # Insert lyrics
                self.conn.execute("""
                    INSERT INTO lyrics (song_id, content, last_updated)
                    SELECT ?, ?, CURRENT_TIMESTAMP
                    WHERE NOT EXISTS (
                        SELECT 1 FROM lyrics WHERE song_id = ?
                    )
                """, [song_id, lyrics, song_id])
            
            if self.verbose:
                self.console.print(
                    f"[bold blue]INFO[/bold blue]     [white]Added '{song_data['name']}' ({views:,} views)"
                )
            
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]ERROR[/bold red]     [white]Failed to process '{song_data['name']}': {str(e)}")
            return False
    
    def create_release_notes(self, new_songs_df: pl.DataFrame) -> str:
        """
        Create release notes in markdown format
        """
        if new_songs_df.is_empty():
            return "Nenhuma nova música foi adicionada nesta atualização."
        
        # Get top 5 artists by views
        top_artists = new_songs_df.group_by('artist_name').agg([
            pl.col('artist_views').first().alias('views'),
            pl.count('name').alias('songs_count')
        ]).sort('views', descending=True).head(5)
        
        # Create markdown
        total_songs = len(new_songs_df)
        total_artists = len(new_songs_df.unique('artist_name'))
        
        notes = f"""# Atualização de Letras Gospel

Nesta atualização, foram adicionadas **{total_songs}** novas músicas de **{total_artists}** artistas.

## Destaques

Os principais artistas desta atualização foram:

"""
        
        for row in top_artists.iter_rows(named=True):
            notes += f"- **{row['artist_name']}** ({row['songs_count']} músicas)\n"
        
        return notes

    def run(self):
        """Main execution flow"""
        self.console.print(Panel.fit(
            "[bold blue]Gospel Lyrics Scraper[/]\n"
            "Collecting and organizing gospel lyrics",
            title="Welcome"
        ))
        
        try:
            # First collect all songs in a DataFrame
            all_songs_df = self.collect_all_songs()
            
            if all_songs_df.is_empty():
                self.console.print("[bold blue]INFO[/bold blue]     [white]No new songs to process")
            else:
                # Process all songs in parallel
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(complete_style="blue"),
                    TextColumn("{task.completed}/{task.total}"),
                    console=self.console
                ) as progress:
                    process_task = progress.add_task(
                        "[bold blue]INFO[/bold blue]     Processing songs...", 
                        total=len(all_songs_df)
                    )
                    
                    completed = 0
                    with ThreadPoolExecutor(max_workers=28) as executor:
                        futures = [
                            executor.submit(self.process_song, song)
                            for song in all_songs_df.iter_rows(named=True)
                        ]
                        
                        for future in as_completed(futures):
                            if future.result():
                                completed += 1
                            progress.update(process_task, completed=completed)
            
            # Create release notes
            release_notes = self.create_release_notes(all_songs_df)
            notes_path = self.data_dir / "RELEASE_NOTES.md"
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(release_notes)
            
            # Create zip with all songs
            archive_path = self.create_archive()
            self.console.print(f"[bold blue]INFO[/bold blue]     [white]Archive created: {archive_path}")
            
            self.console.print(Panel.fit(
                f"[bold green]Process completed successfully![/]\n"
                f"New songs processed: {completed}/{len(all_songs_df)}",
                title="Completed"
            ))
            
        except Exception as e:
            self.console.print(f"[bold red]ERROR[/bold red]     [white]Execution error: {str(e)}")
            raise

    def get_artist_views(self, artist_slug: str) -> int:
        """Get artist views from their page"""
        response = requests.get(f"{self.config.base_url}/{artist_slug}/")
        soup = BeautifulSoup(response.text, 'html.parser')
        return extract_artist_views(soup)
    
    def scrape_artists(self):
        return get_artists()
    
    def scrape_songs(self, artist_slug):
        return get_artist_songs(artist_slug)
    
    def scrape_lyrics(self, artist_slug, song_slug):
        return get_artist_song_lyrics(artist_slug, song_slug)
    
    def save_lyrics_file(self, artist, title, lyrics):
        filename = sanitize_filename(f"{artist} - {title}.txt")
        file_path = self.temp_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{title}\n{artist}\n\n{lyrics}")
            
    def create_archive(self):
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_name = f"lyrics-{timestamp}.zip"
        archive_path = self.data_dir / archive_name
        
        shutil.make_archive(
            str(archive_path.with_suffix("")),
            "zip",
            self.temp_dir
        )
        
        shutil.rmtree(self.temp_dir)
        
        return archive_path