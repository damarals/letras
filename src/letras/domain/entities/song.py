from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Song:
    name: str
    slug: str
    artist_id: int
    views: int = 0
    id: Optional[int] = None
    added_date: Optional[datetime] = None

    @property
    def url(self) -> str:
        return self.slug
