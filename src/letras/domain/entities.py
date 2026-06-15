"""Domain value objects. Identity (ids) is the store's concern, not the entity's."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Song:
    name: str
    slug: str


@dataclass(frozen=True)
class Artist:
    name: str
    slug: str
