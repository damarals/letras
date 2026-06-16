"""Build a Release from the corpus: stamp Admission, then emit the .db, a
per-song .txt ZIP of admitted songs, and notes (ADR-0002)."""

import shutil
import zipfile
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
    scraped = 0
    for row in store.iter_for_admission():
        scraped += 1
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
    used_names: set[str] = set()
    with zipfile.ZipFile(out_dir / "letras.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for artist, song, content in rows:
            filename = _unique_filename(artist, song, used_names)
            used_names.add(filename)
            archive.writestr(filename, f"{song.name}\n{artist.name}\n\n{content}")

    (out_dir / "RELEASE_NOTES.md").write_text(
        _render_notes(rows, date, scraped), encoding="utf-8"
    )


def _unique_filename(artist: Artist, song: Song, used: set[str]) -> str:
    """A ZIP-safe ``Artist - Song.txt`` name, disambiguated by the (globally
    unique) song slug if two songs would otherwise collide — so no song is
    silently overwritten in the archive."""
    base = f"{artist.name} - {song.name}"
    name = f"{base}.txt".replace("/", "_")
    suffix = 0
    while name in used:
        suffix += 1
        tag = song.slug if suffix == 1 else f"{song.slug}-{suffix}"
        name = f"{base} ({tag}).txt".replace("/", "_")
    return name


def _thousands(value: int) -> str:
    """Format an integer with Brazilian thousands separators (1234 -> '1.234')."""
    return f"{value:,}".replace(",", ".")


def _render_notes(rows: list[tuple[Artist, Song, str]], date: str, scraped: int) -> str:
    """Concise, bounded release notes (in Portuguese — the one audience-facing
    artifact). The full per-artist breakdown lives in ``corpus.db`` (queryable);
    listing every artist here would blow past GitHub's 125,000-character
    release-body limit."""
    artists = len({artist.slug for artist, _, _ in rows})
    return (
        "\n".join(
            [
                f"# Letras Gospel — {date}",
                "",
                "Letras gospel em português coletadas de letras.mus.br e "
                "curadas para o corpus.",
                "",
                "| Métrica | Total |",
                "|---|---|",
                f"| Músicas (admitidas) | {_thousands(len(rows))} |",
                f"| Artistas | {_thousands(artists)} |",
                f"| Coletadas (brutas) | {_thousands(scraped)} |",
                f"| Gerado em | {date} |",
                "",
                "## Downloads",
                "- `corpus.db` — corpus completo em SQLite "
                "(artists, songs, lyrics, language)",
                "- `letras.zip` — um `.txt` por música (`Artista - Música.txt`)",
            ]
        )
        + "\n"
    )
