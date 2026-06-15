"""Pure HTML → domain parsing. All site-specific selectors live here."""

import re

from lxml import html as lxml_html
from lxml.etree import LxmlError, _Element

from letras.domain.entities import Artist, Song


class ParseError(Exception):
    """Raised when the page structure does not match expectations (site drift)."""


# Characters libxml2 refuses inside a text node — everything XML 1.0 forbids bar
# tab/newline/carriage-return. Some live lyric pages carry a stray control byte;
# strip it so the page still parses and the byte never reaches the corpus.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _tree(html: str) -> _Element:
    """Parse HTML to an element tree, normalizing failures to ``ParseError``.

    Strips XML-incompatible control characters first, then turns lxml's own
    parse failures (e.g. an empty body) into ``ParseError`` so every parser
    obeys one contract: return a value, or raise ``ParseError`` for callers to
    skip — no raw lxml/``ValueError`` ever leaks out to abort a run.
    """
    try:
        return lxml_html.fromstring(_CONTROL_CHARS.sub("", html))
    except LxmlError as exc:
        raise ParseError("unparseable HTML") from exc


def _collapsed_text(element: _Element) -> str:
    text = "".join(t for t in element.itertext() if isinstance(t, str))
    return " ".join(text.split())


def parse_song(html: str) -> str:
    """Extract a song's lyrics, preserving stanzas and line breaks.

    Within ``div.lyric-original`` each ``<p>`` is a stanza and each ``<br>`` a
    line break; stanzas are joined by a blank line.
    """
    tree = _tree(html)
    containers = tree.cssselect("div.lyric-original")
    if not containers:
        raise ParseError("no div.lyric-original element found")
    container = containers[0]
    stanzas = []
    for paragraph in container.cssselect("p"):
        for br in paragraph.iter("br"):
            br.tail = "\n" + (br.tail or "")
        text = "".join(t for t in paragraph.itertext() if isinstance(t, str))
        lines = [line.strip() for line in text.split("\n")]
        stanzas.append("\n".join(lines))
    return "\n\n".join(stanzas)


def parse_artist_songs(html: str) -> list[Song]:
    """Extract an artist's songs (name + slug) from their page."""
    tree = _tree(html)
    songs = []
    for anchor in tree.cssselect("a.songList-table-songName"):
        href = anchor.get("href") or ""
        slug = href.strip("/").split("/")[-1]
        songs.append(Song(name=_collapsed_text(anchor), slug=slug))
    return songs


def parse_artist_index(html: str) -> list[Artist]:
    """Extract all artists (name + slug) from the gospel index fragment."""
    tree = _tree(html)
    artists = []
    for anchor in tree.cssselect("ul.cnt-list a"):
        href = anchor.get("href") or ""
        artists.append(Artist(name=_collapsed_text(anchor), slug=href.strip("/")))
    if not artists:
        raise ParseError("no artists found in index")
    return artists
