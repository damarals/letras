"""Build a Release from the corpus: the .db, a per-song .txt ZIP, and notes.

For now everything in the store is exported; Admission filtering arrives in a
later slice (it will export only `admitted` rows).
"""

import shutil
import zipfile
from collections import Counter
from pathlib import Path

from letras.domain.entities import Artist, Song
from letras.store.corpus_store import CorpusStore


def export_release(store: CorpusStore, db_path: Path, out_dir: Path, date: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(db_path, out_dir / "corpus.db")

    rows = list(store.iter_export())
    with zipfile.ZipFile(
        out_dir / f"lyrics-{date}.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for artist, song, content in rows:
            filename = f"{artist.name} - {song.name}.txt".replace("/", "_")
            archive.writestr(filename, f"{song.name}\n{artist.name}\n\n{content}")

    (out_dir / "RELEASE_NOTES.md").write_text(
        _render_notes(rows, date), encoding="utf-8"
    )


def _render_notes(rows: list[tuple[Artist, Song, str]], date: str) -> str:
    songs_per_artist: Counter[str] = Counter(artist.name for artist, _, _ in rows)
    lines = [
        f"# Letras Gospel — {date}",
        "",
        f"{len(rows)} songs from {len(songs_per_artist)} artists.",
        "",
        "## Artists",
    ]
    lines += [f"- {name} ({count} songs)" for name, count in songs_per_artist.most_common()]
    return "\n".join(lines) + "\n"
