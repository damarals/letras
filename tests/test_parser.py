from pathlib import Path

from letras.domain.entities import Artist, Song
from letras.source.parser import parse_artist_index, parse_artist_songs, parse_song

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_song_preserves_stanzas_and_line_breaks() -> None:
    html = (FIXTURES / "song_page.html").read_text(encoding="utf-8")

    content = parse_song(html)

    # <br> becomes a newline within a stanza; each <p> is separated by a blank line.
    assert content.startswith(
        "Ao Rei dos reis, consagro tudo o que sou\n"
        "De gratos louvores, transborda o meu coração\n"
        "A minha vida, eu entrego nas Tuas mãos, meu Senhor\n"
        "Pra Te exaltar com todo meu amor\n"
        "\n"
        "Eu Te louvarei conforme a Tua justiça\n"
        "E cantarei louvores\n"
        "Pois Tu és altíssimo"
    )


def test_parse_artist_songs_extracts_name_and_slug_ignoring_junk_links() -> None:
    html = (FIXTURES / "artist_page.html").read_text(encoding="utf-8")

    songs = parse_artist_songs(html)

    assert len(songs) == 10
    # numeric-id slug and text slug are both taken from the last path segment
    assert Song(name="Consagração", slug="44039") in songs
    assert any(s.slug == "jeova-jireh" for s in songs)
    # the ouvir.html header button is not a songName link, so it is excluded
    assert all("ouvir" not in s.slug for s in songs)


def test_parse_artist_index_extracts_name_and_slug() -> None:
    html = (FIXTURES / "artist_index.html").read_text(encoding="utf-8")

    artists = parse_artist_index(html)

    assert len(artists) == 12
    assert artists[0] == Artist(
        name="1° Igreja Batista Em Trindade", slug="1-igreja-batista-em-trindade"
    )
    # HTML entities are decoded
    assert Artist(name="10,000 Fathers & Mothers", slug="10-000-fathers-e-mothers") in artists
