from letras.domain.admission import admit
from letras.domain.policy import load_policy

POLICY = load_policy()
# ~205 chars of clean Portuguese gospel text with no excluded terms.
GOOD_LYRIC = "Louvarei ao Senhor de todo o meu coração e exaltarei o Teu nome " * 4


def test_load_policy_reads_filters_yaml() -> None:
    policy = load_policy()

    assert policy.language == "pt"
    assert policy.min_length == 100
    assert policy.max_length == 4000
    assert "Padre" in policy.artist_excludes
    assert "Ave Maria" in policy.title_excludes
    assert "macumba" in policy.content_excludes


def test_admit_accepts_conforming_portuguese_lyric() -> None:
    verdict = admit(
        artist_name="Aline Barros",
        song_name="Consagração",
        content=GOOD_LYRIC,
        language="pt",
        policy=POLICY,
    )
    assert verdict.admitted is True
    assert verdict.reason is None


def test_admit_rejects_non_portuguese() -> None:
    verdict = admit(
        artist_name="Hillsong",
        song_name="Oceans",
        content=GOOD_LYRIC,
        language="en",
        policy=POLICY,
    )
    assert verdict.admitted is False
    assert verdict.reason == "language"


def test_admit_rejects_lyrics_outside_length_bounds() -> None:
    too_short = admit(
        artist_name="A", song_name="S", content="curta demais",
        language="pt", policy=POLICY,
    )
    assert (too_short.admitted, too_short.reason) == (False, "length")

    too_long = admit(
        artist_name="A", song_name="S", content="palavra " * 1000,
        language="pt", policy=POLICY,
    )
    assert (too_long.admitted, too_long.reason) == (False, "length")


def test_admit_rejects_excluded_artist_title_or_content() -> None:
    assert admit(
        artist_name="Padre Marcelo Rossi", song_name="S",
        content=GOOD_LYRIC, language="pt", policy=POLICY,
    ).reason == "artist"
    assert admit(
        artist_name="Coral X", song_name="Ave Maria",
        content=GOOD_LYRIC, language="pt", policy=POLICY,
    ).reason == "title"
    assert admit(
        artist_name="A", song_name="S",
        content=GOOD_LYRIC + " fui ao terreiro fazer macumba",
        language="pt", policy=POLICY,
    ).reason == "content"


def test_admit_does_not_overmatch_substrings() -> None:
    # "Padreira" is a surname; the whole-word rule must not treat it as "Padre".
    verdict = admit(
        artist_name="Ana Padreira", song_name="S",
        content=GOOD_LYRIC, language="pt", policy=POLICY,
    )
    assert verdict.admitted is True
