import asyncio
from pathlib import Path

import pytest

from letras.domain.entities.artist import Artist
from letras.domain.entities.song import Song
from letras.domain.services.language_service import LanguageService
from letras.domain.services.lyrics_service import LyricsService
from letras.infrastructure.database.connection import PostgresConnection
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)
from letras.infrastructure.web.scraper import WebScraper


@pytest.fixture
async def postgres_connection(db_config):
    """Database connection for e2e tests"""
    conn = PostgresConnection(**db_config)
    try:
        await conn.initialize()
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def repository(postgres_connection):
    """Repository for e2e tests"""
    repo = PostgresRepository(postgres_connection)
    # Clean data before each test
    async with postgres_connection.transaction() as conn:
        await conn.execute("TRUNCATE lyrics, songs, artists CASCADE")
    return repo


@pytest.fixture
async def scraper():
    """Real scraper for e2e tests"""
    scraper = WebScraper(base_url="https://www.letras.mus.br")
    await scraper.initialize()
    try:
        yield scraper
    finally:
        await scraper.close()


@pytest.fixture
async def lyrics_service(repository, scraper):
    """Service that coordinates all components"""
    language_service = LanguageService()
    return LyricsService(
        repository=repository, language_service=language_service, scraper=scraper
    )


@pytest.mark.asyncio
async def test_lyrics_end_to_end(repository, lyrics_service, scraper, tmp_path):
    """Test complete flow: from web scraping to file creation"""
    # Setup - test directory
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initial scraping
    print("\nPerforming song scraping...")
    artist = Artist(name="Aline Barros", slug="aline-barros")
    song = Song(
        name="Ressuscita-me",
        slug="1819226",
        artist_id=None,  # Will be set after artist processing
    )

    # 2. Artist processing
    processed_artist = await lyrics_service.process_artist(artist)
    assert processed_artist is not None
    print(f"Processed artist: {processed_artist.name} (ID: {processed_artist.id})")

    # 3. Get and verify original lyrics
    song.artist_id = processed_artist.id
    scrape_result = await scraper.get_song_details(processed_artist, song)
    assert scrape_result is not None

    print("\nOriginal scraped content:")
    print(repr(scrape_result.content))
    assert "\n" in scrape_result.content, "No line breaks in original content"

    # 4. Save to database
    processed_song = await repository.add_song(song)
    assert processed_song.id is not None
    print(f"\nSong saved to database: {processed_song.name} (ID: {processed_song.id})")

    # 5. Process and verify lyrics
    lyrics = await lyrics_service.process_lyrics(processed_artist, processed_song)
    assert lyrics is not None
    print("\nLyrics after processing:")
    print(repr(lyrics.content))

    # 6. Retrieve from database to check persistence
    stored_lyrics = await repository.get_lyrics_by_song(processed_song.id)
    assert stored_lyrics is not None
    print("\nLyrics retrieved from database:")
    print(repr(stored_lyrics.content))

    # 7. Verify line breaks were preserved
    assert stored_lyrics.content == scrape_result.content, (
        "Line breaks changed during storage.\n"
        f"Original:\n{repr(scrape_result.content)}\n"
        f"Stored:\n{repr(stored_lyrics.content)}"
    )

    # 8. Generate final file
    filename = f"{processed_artist.name} - {processed_song.name}.txt".replace("/", "_")
    filepath = temp_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            f"{processed_song.name}\n{processed_artist.name}\n\n{stored_lyrics.content}"
        )

    # 9. Check generated file
    print(f"\nGenerated file content {filename}:")
    content = filepath.read_text(encoding="utf-8")
    print(repr(content))

    # Split header from lyrics
    _, lyrics_content = content.split("\n\n", 1)

    assert lyrics_content == scrape_result.content, (
        "Line breaks changed during file generation.\n"
        f"Original:\n{repr(scrape_result.content)}\n"
        f"File:\n{repr(lyrics_content)}"
    )


@pytest.mark.asyncio
async def test_multiple_songs_end_to_end(repository, lyrics_service, scraper, tmp_path):
    """Test complete flow with multiple songs to ensure consistency"""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    songs_to_test = [
        ("Aline Barros", "aline-barros", "Ressuscita-me", "1819226"),
        ("Aline Barros", "aline-barros", "Jeová Jireh", "jeova-jireh"),
    ]

    for artist_name, artist_slug, song_name, song_slug in songs_to_test:
        print(f"\nProcessing {artist_name} - {song_name}")

        # Process artist
        artist = Artist(name=artist_name, slug=artist_slug)
        processed_artist = await lyrics_service.process_artist(artist)
        assert processed_artist is not None, f"Failed to process artist {artist_name}"
        print(f"Artist processed successfully (ID: {processed_artist.id})")

        # Process song
        song = Song(name=song_name, slug=song_slug, artist_id=processed_artist.id)

        # Get original content
        print(f"Fetching song details for {song_name}...")
        scrape_result = await scraper.get_song_details(processed_artist, song)
        assert (
            scrape_result is not None
        ), f"Failed to get details for {song_name} (slug: {song_slug})"
        print(f"Song details fetched successfully")

        original_content = scrape_result.content
        print(f"\nOriginal content first few lines:")
        for line in original_content.split("\n")[:3]:
            print(repr(line))

        # Save and retrieve from database
        processed_song = await repository.add_song(song)
        print(f"Song saved to database (ID: {processed_song.id})")

        lyrics = await lyrics_service.process_lyrics(processed_artist, processed_song)
        assert lyrics is not None, f"Failed to process lyrics for {song_name}"
        print("Lyrics processed successfully")

        stored_lyrics = await repository.get_lyrics_by_song(processed_song.id)
        assert stored_lyrics is not None, f"Failed to retrieve lyrics for {song_name}"
        print("Lyrics retrieved from database successfully")

        assert stored_lyrics.content == original_content, (
            f"Line breaks changed for {song_name}.\n"
            f"Original:\n{repr(original_content)}\n"
            f"Stored:\n{repr(stored_lyrics.content)}"
        )
        print("Content verification passed")

        # Generate file
        filename = f"{processed_artist.name} - {processed_song.name}.txt".replace(
            "/", "_"
        )
        filepath = temp_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(
                f"{processed_song.name}\n{processed_artist.name}\n\n{stored_lyrics.content}"
            )
        print(f"File generated: {filename}")

        # Verify file content
        content = filepath.read_text(encoding="utf-8")
        _, lyrics_content = content.split("\n\n", 1)

        assert lyrics_content == original_content, (
            f"Line breaks changed in file for {song_name}.\n"
            f"Original:\n{repr(original_content)}\n"
            f"File:\n{repr(lyrics_content)}"
        )
        print("File content verification passed")

        # Longer pause between requests
        print("Waiting before next request...")
        await asyncio.sleep(2)
