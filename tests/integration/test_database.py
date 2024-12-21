import asyncio
from datetime import datetime

import pytest

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song
from letras.infrastructure.database.connection import PostgresConnection
from letras.infrastructure.database.repositories.postgres_repository import (
    PostgresRepository,
)


@pytest.fixture
async def postgres_connection(db_config):
    """Test database connection"""
    conn = PostgresConnection(**db_config)
    try:
        await conn.initialize()
        yield conn
    finally:
        await conn.close()


@pytest.fixture
async def repository(postgres_connection):
    """Test repository"""
    repo = PostgresRepository(postgres_connection)
    # Clean data before each test
    async with postgres_connection.transaction() as conn:
        await conn.execute("TRUNCATE lyrics, songs, artists CASCADE")
    return repo


@pytest.mark.asyncio
async def test_full_crud_flow(repository):
    # Create artist
    artist = await repository.add_artist(
        Artist(name="Test Artist", slug="test-artist", views=1000)
    )
    assert artist.id is not None

    # Get artist by slug
    found = await repository.get_artist_by_slug("test-artist")
    assert found.name == artist.name

    # Update views
    await repository.update_artist_views(artist.id, 2000)
    updated = await repository.get_artist_by_id(artist.id)
    assert updated.views == 2000

    # Add song
    song = await repository.add_song(
        Song(name="Test Song", slug="test-song", artist_id=artist.id, views=500)
    )
    assert song.id is not None

    # Get artist songs
    songs = await repository.get_songs_by_artist(artist.id)
    assert len(songs) == 1
    assert songs[0].name == song.name

    # Add lyrics
    lyrics = await repository.add_lyrics(
        Lyrics(song_id=song.id, content="Test lyrics content")
    )
    assert lyrics.id is not None

    # Get lyrics
    found_lyrics = await repository.get_lyrics_by_song(song.id)
    assert found_lyrics.content == lyrics.content


@pytest.mark.asyncio
async def test_concurrent_access(repository):
    # Create base artist
    artist = await repository.add_artist(
        Artist(name="Base Artist", slug="base-artist", views=1000)
    )

    # Concurrent song additions
    async def add_song(i: int):
        return await repository.add_song(
            Song(name=f"Song {i}", slug=f"song-{i}", artist_id=artist.id, views=i * 100)
        )

    songs = await asyncio.gather(*[add_song(i) for i in range(10)])
    assert len(songs) == 10
    assert len({s.id for s in songs}) == 10  # All unique IDs


@pytest.mark.asyncio
async def test_transaction_rollback(repository, postgres_connection):
    # The rollback should happen automatically when the transaction fails
    artist_data = Artist(name="Rollback Test", slug="rollback-test")

    try:
        async with postgres_connection.transaction() as conn:
            # Set the current transaction
            repository._current_transaction = conn
            # Add artist
            await repository.add_artist(artist_data)
            # Force error
            await conn.execute("SELECT invalid_column")
    except:
        pass  # We expect the transaction to fail
    finally:
        # Clear transaction context
        repository._current_transaction = None

    # Artist should not exist after rollback
    found = await repository.get_artist_by_slug("rollback-test")
    assert found is None


@pytest.mark.asyncio
async def test_bulk_operations(repository):
    # Bulk artist creation
    artists = [
        Artist(name=f"Artist {i}", slug=f"artist-{i}", views=i * 100) for i in range(10)
    ]

    async def add_artist(artist):
        return await repository.add_artist(artist)

    created = await asyncio.gather(*[add_artist(a) for a in artists])
    assert len(created) == 10

    # Verify all were created
    all_artists = await repository.get_all_artists()
    assert len(all_artists) == 10  # Should be exactly 10


@pytest.mark.asyncio
async def test_lyrics_line_breaks(repository):
    # Create artist and song
    artist = await repository.add_artist(
        Artist(name="Test Artist", slug="test-artist", views=1000)
    )
    song = await repository.add_song(
        Song(name="Test Song", slug="test-song", artist_id=artist.id, views=500)
    )

    # Test lyrics with different line break scenarios
    test_lyrics = (
        "First line\n"
        "Second line\n"
        "\n"
        "Fourth line after empty line\n"
        "Last line"
    )

    # Add lyrics
    lyrics = await repository.add_lyrics(
        Lyrics(song_id=song.id, content=test_lyrics)
    )

    # Get lyrics back
    found_lyrics = await repository.get_lyrics_by_song(song.id)
    
    # Verify content is exactly the same, including line breaks
    assert found_lyrics.content == test_lyrics, (
        "Line breaks in lyrics were not preserved.\n"
        f"Expected:\n{repr(test_lyrics)}\n"
        f"Got:\n{repr(found_lyrics.content)}"
    )