"""The corpus store: a single SQLite file, raw SQL, no ORM (ADR-0001, ADR-0003)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from letras.domain.entities import Artist, Song

_SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    slug       TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS songs (
    id         INTEGER PRIMARY KEY,
    artist_id  INTEGER NOT NULL REFERENCES artists(id),
    name       TEXT NOT NULL,
    slug       TEXT NOT NULL,
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (artist_id, slug)
);
CREATE TABLE IF NOT EXISTS lyrics (
    song_id    INTEGER PRIMARY KEY REFERENCES songs(id),
    content    TEXT NOT NULL,
    language   TEXT,
    char_count INTEGER NOT NULL,
    admitted   INTEGER NOT NULL DEFAULT 0,
    scraped_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist_id);
"""


class CorpusStore:
    def __init__(self, path: str | Path) -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)

    def upsert_artist(self, artist: Artist) -> int:
        cur = self._conn.execute(
            "INSERT INTO artists (name, slug) VALUES (?, ?) "
            "ON CONFLICT(slug) DO UPDATE SET name = excluded.name RETURNING id",
            (artist.name, artist.slug),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row[0])

    def upsert_song(self, song: Song, artist_id: int) -> int:
        cur = self._conn.execute(
            "INSERT INTO songs (name, slug, artist_id) VALUES (?, ?, ?) "
            "ON CONFLICT(artist_id, slug) DO UPDATE SET name = excluded.name RETURNING id",
            (song.name, song.slug, artist_id),
        )
        row = cur.fetchone()
        self._conn.commit()
        return int(row[0])

    def set_lyrics(
        self, song_id: int, content: str, language: str | None, char_count: int
    ) -> None:
        self._conn.execute(
            "INSERT INTO lyrics (song_id, content, language, char_count) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(song_id) DO UPDATE SET content = excluded.content, "
            "language = excluded.language, char_count = excluded.char_count",
            (song_id, content, language, char_count),
        )
        self._conn.commit()

    def known_song_slugs(self, artist_id: int) -> set[str]:
        cur = self._conn.execute(
            "SELECT slug FROM songs WHERE artist_id = ?", (artist_id,)
        )
        return {str(row[0]) for row in cur.fetchall()}

    def iter_export(self) -> Iterator[tuple[Artist, Song, str]]:
        cur = self._conn.execute(
            "SELECT a.name, a.slug, s.name, s.slug, l.content "
            "FROM lyrics l "
            "JOIN songs s ON s.id = l.song_id "
            "JOIN artists a ON a.id = s.artist_id "
            "ORDER BY a.name, s.name"
        )
        for row in cur.fetchall():
            yield (
                Artist(name=str(row[0]), slug=str(row[1])),
                Song(name=str(row[2]), slug=str(row[3])),
                str(row[4]),
            )

    def iter_for_admission(self) -> Iterator[tuple[int, str, str, str, str]]:
        """Yield (song_id, artist_name, song_name, content, language) per lyric."""
        cur = self._conn.execute(
            "SELECT l.song_id, a.name, s.name, l.content, l.language "
            "FROM lyrics l "
            "JOIN songs s ON s.id = l.song_id "
            "JOIN artists a ON a.id = s.artist_id"
        )
        for row in cur.fetchall():
            yield (
                int(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                str(row[4] or ""),
            )

    def set_admitted(self, song_id: int, admitted: bool) -> None:
        self._conn.execute(
            "UPDATE lyrics SET admitted = ? WHERE song_id = ?",
            (1 if admitted else 0, song_id),
        )
        self._conn.commit()

    def iter_admitted(self) -> Iterator[tuple[Artist, Song, str]]:
        cur = self._conn.execute(
            "SELECT a.name, a.slug, s.name, s.slug, l.content "
            "FROM lyrics l "
            "JOIN songs s ON s.id = l.song_id "
            "JOIN artists a ON a.id = s.artist_id "
            "WHERE l.admitted = 1 "
            "ORDER BY a.name, s.name"
        )
        for row in cur.fetchall():
            yield (
                Artist(name=str(row[0]), slug=str(row[1])),
                Song(name=str(row[2]), slug=str(row[3])),
                str(row[4]),
            )

    def close(self) -> None:
        self._conn.close()
