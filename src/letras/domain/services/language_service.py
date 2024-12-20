import re

from lingua import Language, LanguageDetectorBuilder


class LanguageService:
    def __init__(self):
        self.detector = LanguageDetectorBuilder.from_languages(
            Language.PORTUGUESE, Language.ENGLISH, Language.SPANISH
        ).build()

    def is_portuguese(self, text: str) -> bool:
        """Check if text is in Portuguese"""
        try:
            # Clean text
            text = self._clean_text(text)
            if not text:
                return False

            # Detect language
            lang = self.detector.detect_language_of(text)
            return lang == Language.PORTUGUESE

        except Exception:
            return False

    def _clean_text(self, text: str) -> str:
        """Clean text for language detection"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())
        # Remove common non-letter patterns
        text = re.sub(r"[0-9]+", "", text)
        text = re.sub(r"[^\w\s]", "", text)
        return text
