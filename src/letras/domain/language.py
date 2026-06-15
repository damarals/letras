"""Language detection, used to label lyrics at scrape time (ISO 639-1, e.g. 'pt')."""

from lingua import Language, LanguageDetectorBuilder

_DETECTOR = LanguageDetectorBuilder.from_languages(
    Language.PORTUGUESE, Language.ENGLISH, Language.SPANISH
).build()


def detect_language(text: str) -> str:
    language = _DETECTOR.detect_language_of(text)
    if language is None:
        return "und"
    code: str = language.iso_code_639_1.name.lower()
    return code
