from letras.domain.language import detect_language


def test_detect_language_identifies_portuguese_and_english() -> None:
    assert (
        detect_language("Louvarei ao Senhor de todo o meu coração para sempre, aleluia")
        == "pt"
    )
    assert (
        detect_language(
            "I will praise the Lord with all of my heart forever, hallelujah"
        )
        == "en"
    )
