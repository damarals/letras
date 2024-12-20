from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Artist:
    name: str
    slug: str
    views: int = 0
    id: Optional[int] = None
    added_date: Optional[datetime] = None

    @property
    def url(self) -> str:
        return f"/{self.slug}/"
