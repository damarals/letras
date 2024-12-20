from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Lyrics:
    song_id: int
    content: str
    last_updated: Optional[datetime] = None
    id: Optional[int] = None
