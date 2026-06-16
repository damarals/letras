"""Build a Release from the corpus: stamp Admission, then emit the .db, a
per-song .txt ZIP, a per-song OpenLyrics .xml ZIP, and notes (ADR-0002)."""

import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
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
    with zipfile.ZipFile(
        out_dir / "letras-txt.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for artist, song, content in rows:
            filename = _unique_filename(artist, song, used_names)
            used_names.add(filename)
            archive.writestr(filename, f"{song.name}\n{artist.name}\n\n{content}")

    xml_names: set[str] = set()
    with zipfile.ZipFile(
        out_dir / "letras-openlyrics.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        for artist, song, content in rows:
            filename = _unique_filename(artist, song, xml_names, "xml")
            xml_names.add(filename)
            archive.writestr(filename, _render_openlyrics(artist, song, content))

    (out_dir / "RELEASE_NOTES.md").write_text(
        _render_notes(rows, date, scraped), encoding="utf-8"
    )


def _unique_filename(
    artist: Artist, song: Song, used: set[str], ext: str = "txt"
) -> str:
    """A ZIP-safe ``Artist - Song.<ext>`` name, disambiguated by the (globally
    unique) song slug if two songs would otherwise collide — so no song is
    silently overwritten in the archive."""
    base = f"{artist.name} - {song.name}"
    name = f"{base}.{ext}".replace("/", "_")
    suffix = 0
    while name in used:
        suffix += 1
        tag = song.slug if suffix == 1 else f"{song.slug}-{suffix}"
        name = f"{base} ({tag}).{ext}".replace("/", "_")
    return name


_OPENLYRICS_NS = "http://openlyrics.info/namespace/2009/song"


def _q(tag: str) -> str:
    """Qualify a tag with the OpenLyrics namespace (Clark notation)."""
    return f"{{{_OPENLYRICS_NS}}}{tag}"


def _stanzas(content: str) -> list[list[str]]:
    """Split a lyric into stanzas (on blank lines), each a list of non-empty
    lines. These map onto OpenLyrics verses."""
    stanzas = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            stanzas.append(lines)
    return stanzas


def _render_openlyrics(artist: Artist, song: Song, content: str) -> str:
    """Render one admitted song as OpenLyrics 0.9 XML, the open format OpenLP
    and Quelea import natively (title and author land in their own fields).
    Stanzas become verses; line breaks within a stanza become ``<br/>``."""
    ET.register_namespace("", _OPENLYRICS_NS)
    song_el = ET.Element(_q("song"), version="0.9", createdIn="letras")

    props = ET.SubElement(song_el, _q("properties"))
    ET.SubElement(ET.SubElement(props, _q("titles")), _q("title")).text = song.name
    ET.SubElement(ET.SubElement(props, _q("authors")), _q("author")).text = artist.name

    lyrics_el = ET.SubElement(song_el, _q("lyrics"))
    for index, lines in enumerate(_stanzas(content) or [[content.strip()]], start=1):
        verse = ET.SubElement(lyrics_el, _q("verse"), name=f"v{index}")
        lines_el = ET.SubElement(verse, _q("lines"))
        lines_el.text = lines[0]
        for line in lines[1:]:
            ET.SubElement(lines_el, _q("br")).tail = line

    body = ET.tostring(song_el, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}\n'


def _thousands(value: int) -> str:
    """Format an integer with Brazilian thousands separators (1234 -> '1.234')."""
    return f"{value:,}".replace(",", ".")


def _format_date_br(stamp: str) -> str:
    """Render a ``YYYYMMDD`` stamp as Brazilian ``DD/MM/YYYY``."""
    return datetime.strptime(stamp, "%Y%m%d").strftime("%d/%m/%Y")


def _render_notes(rows: list[tuple[Artist, Song, str]], date: str, scraped: int) -> str:
    """Concise, bounded release notes (in Portuguese — the one audience-facing
    artifact). The full per-artist breakdown lives in ``corpus.db`` (queryable);
    listing every artist here would blow past GitHub's 125,000-character
    release-body limit."""
    artists = len({artist.slug for artist, _, _ in rows})
    return (
        "\n".join(
            [
                "# Letras gospel em português",
                "",
                "Milhares de letras de músicas evangélicas coletadas de "
                "letras.mus.br.",
                "",
                "| Métrica | Total |",
                "|---|---|",
                f"| Músicas (admitidas) | {_thousands(len(rows))} |",
                f"| Artistas | {_thousands(artists)} |",
                f"| Coletadas (brutas) | {_thousands(scraped)} |",
                f"| Gerado em | {_format_date_br(date)} |",
                "",
                "## Downloads",
                "- `letras-txt.zip`: um `.txt` por música (`Artista - Música.txt`)",
                "- `letras-openlyrics.zip`: um `.xml` por música, "
                "formato OpenLyrics (OpenLP, Quelea)",
                "- `corpus.db`: tudo em um arquivo SQLite "
                "(artists, songs, lyrics, language)",
            ]
        )
        + "\n"
    )
