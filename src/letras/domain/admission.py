"""Admission: the pure decision of whether a lyric belongs in the corpus."""

import re
import unicodedata
from dataclasses import dataclass

from letras.domain.policy import AdmissionPolicy


@dataclass(frozen=True)
class Verdict:
    admitted: bool
    reason: str | None = None


def _normalize(text: str) -> str:
    """Lowercase and strip accents, so matching is case- and accent-insensitive."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _matches_any(text: str, keywords: list[str]) -> bool:
    normalized = _normalize(text)
    return any(
        re.search(rf"\b{re.escape(_normalize(keyword))}\b", normalized)
        for keyword in keywords
    )


def admit(
    *,
    artist_name: str,
    song_name: str,
    content: str,
    language: str,
    policy: AdmissionPolicy,
) -> Verdict:
    if language != policy.language:
        return Verdict(admitted=False, reason="language")
    if not policy.min_length <= len(content) <= policy.max_length:
        return Verdict(admitted=False, reason="length")
    if _matches_any(artist_name, policy.artist_excludes):
        return Verdict(admitted=False, reason="artist")
    if _matches_any(song_name, policy.title_excludes):
        return Verdict(admitted=False, reason="title")
    if _matches_any(content, policy.content_excludes):
        return Verdict(admitted=False, reason="content")
    return Verdict(admitted=True)
