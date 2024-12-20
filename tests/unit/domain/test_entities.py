from datetime import datetime

from letras.domain.entities.artist import Artist
from letras.domain.entities.lyrics import Lyrics
from letras.domain.entities.song import Song


class TestArtist:
    def test_artist_creation(self):
        artist = Artist(
            name="Test Artist",
            slug="test-artist",
            views=1000,
            id=1,
            added_date=datetime.now(),
        )

        assert artist.name == "Test Artist"
        assert artist.slug == "test-artist"
        assert artist.views == 1000
        assert artist.id == 1
        assert isinstance(artist.added_date, datetime)

    def test_artist_url_property(self):
        artist = Artist(name="Test", slug="test-artist")
        assert artist.url == "/test-artist/"

    def test_artist_equality(self):
        artist1 = Artist(name="Test", slug="test", id=1)
        artist2 = Artist(name="Test", slug="test", id=1)
        artist3 = Artist(name="Test", slug="test", id=2)

        assert artist1 == artist2
        assert artist1 != artist3


class TestSong:
    def test_song_creation(self):
        song = Song(
            name="Test Song",
            slug="test-song",
            artist_id=1,
            views=500,
            id=1,
            added_date=datetime.now(),
        )

        assert song.name == "Test Song"
        assert song.slug == "test-song"
        assert song.artist_id == 1
        assert song.views == 500
        assert song.id == 1
        assert isinstance(song.added_date, datetime)

    def test_song_url_property(self):
        song = Song(name="Test", slug="test-song", artist_id=1)
        assert song.url == "test-song"

    def test_song_equality(self):
        song1 = Song(name="Test", slug="test", artist_id=1, id=1)
        song2 = Song(name="Test", slug="test", artist_id=1, id=1)
        song3 = Song(name="Test", slug="test", artist_id=1, id=2)

        assert song1 == song2
        assert song1 != song3


class TestLyrics:
    def test_lyrics_creation(self):
        lyrics = Lyrics(
            song_id=1, content="Test lyrics content", last_updated=datetime.now(), id=1
        )

        assert lyrics.song_id == 1
        assert lyrics.content == "Test lyrics content"
        assert lyrics.id == 1
        assert isinstance(lyrics.last_updated, datetime)

    def test_lyrics_equality(self):
        lyrics1 = Lyrics(song_id=1, content="Test", id=1)
        lyrics2 = Lyrics(song_id=1, content="Test", id=1)
        lyrics3 = Lyrics(song_id=1, content="Different", id=1)

        assert lyrics1 == lyrics2
        assert lyrics1 != lyrics3

    def test_lyrics_content_normalization(self):
        content = "  Line 1\n\nLine 2  \n\n  Line 3  "
        lyrics = Lyrics(song_id=1, content=content)
        assert lyrics.content == content
