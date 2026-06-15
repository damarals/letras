"""Build a Release from the corpus: stamp Admission, then emit the .db, a
per-song .txt ZIP of admitted songs, and notes (ADR-0002)."""

import shutil
import zipfile
from collections import Counter
from pathlib import Path

from letras.domain.admission import admit
from letras.domain.entities import Artist, Song
from letras.domain.policy import AdmissionPolicy
from letras.store.corpus_store import CorpusStore


def export_release(
    store: CorpusStore,
    db_path: Path,
    out_dir: Path,
    date: str,
    policy: AdmissionPolicy,
) -> None:
    for row in store.iter_for_admission():
        song_id, artist_name, song_name, content, language = row
        verdict = admit(
            artist_name=artist_name,
            song_name=song_name,
            content=content,
            language=language,
            policy=policy,
        )
        store.set_admitted(song_id, verdict.admitted)

    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(db_path, out_dir / "corpus.db")

    rows = list(store.iter_admitted())
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
    lines += [
        f"- {name} ({count} songs)" for name, count in songs_per_artist.most_common()
    ]
    return "\n".join(lines) + "\n"
