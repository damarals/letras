"""Pure HTML → domain parsing. All site-specific selectors live here."""

from lxml import html as lxml_html
from lxml.etree import _Element

from letras.domain.entities import Artist, Song


def _collapsed_text(element: _Element) -> str:
    text = "".join(t for t in element.itertext() if isinstance(t, str))
    return " ".join(text.split())


def parse_song(html: str) -> str:
    """Extract a song's lyrics, preserving stanzas and line breaks.

    Within ``div.lyric-original`` each ``<p>`` is a stanza and each ``<br>`` a
    line break; stanzas are joined by a blank line.
    """
    tree = lxml_html.fromstring(html)
    container = tree.cssselect("div.lyric-original")[0]
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
    tree = lxml_html.fromstring(html)
    songs = []
    for anchor in tree.cssselect("a.songList-table-songName"):
        href = anchor.get("href") or ""
        slug = href.strip("/").split("/")[-1]
        songs.append(Song(name=_collapsed_text(anchor), slug=slug))
    return songs


def parse_artist_index(html: str) -> list[Artist]:
    """Extract all artists (name + slug) from the gospel index fragment."""
    tree = lxml_html.fromstring(html)
    artists = []
    for anchor in tree.cssselect("ul.cnt-list a"):
        href = anchor.get("href") or ""
        artists.append(Artist(name=_collapsed_text(anchor), slug=href.strip("/")))
    return artists
