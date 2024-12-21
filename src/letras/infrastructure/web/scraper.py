import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from letras.domain.entities.artist import Artist
from letras.domain.entities.song import Song


@dataclass
class ScrapeResult:
    content: str
    views: int


class WebScraper:
    def __init__(self, base_url: str, max_workers: int = 10):
        self._base_url = base_url
        self._logger = logging.getLogger(__name__)
        self._rate_limiter = asyncio.Semaphore(max_workers)
        self._session = None

    async def initialize(self):
        """Initialize HTTP session"""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100, enable_cleanup_closed=True),
                headers={"User-Agent": "Mozilla/5.0 (compatible; Letras/1.0)"},
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=10))
    async def _get(self, url: str) -> str:
        """Make GET request with retry"""
        if not self._session:
            await self.initialize()

        async with self._rate_limiter:
            async with self._session.get(f"{self._base_url}{url}") as response:
                response.raise_for_status()
                return await response.text(encoding="utf-8", errors="ignore")

    async def get_all_artists(self) -> List[Artist]:
        """Get all gospel artists"""
        html = await self._get("/estilos/gospelreligioso/todosartistas.html")
        soup = BeautifulSoup(html, "html.parser")

        return [
            Artist(name=link.text.strip(), slug=link["href"].strip("/"))
            for link in soup.find_all("a", href=True)
            if link["href"].strip("/") and "/" not in link["href"].strip("/")
        ]

    async def get_artist_details(self, artist: Artist) -> Optional[ScrapeResult]:
        """Get artist views"""
        try:
            html = await self._get(artist.url)
            soup = BeautifulSoup(html, "html.parser")
            views_div = soup.find("div", class_="head-info-exib")
            if views_div and (views_text := views_div.find("b")):
                return ScrapeResult(
                    content="", views=int(views_text.text.replace(".", ""))
                )
            return None
        except Exception as e:
            self._logger.error(f"Error getting artist details: {e}")
            return None

    async def get_artist_songs(self, artist: Artist) -> List[Song]:
        """Get artist songs"""
        try:
            html = await self._get(artist.url)
            soup = BeautifulSoup(html, "html.parser")
            songs = []

            for song_div in soup.find_all("li", class_="songList-table-row"):
                if link := song_div.find("a", class_="songList-table-songName"):
                    songs.append(
                        Song(
                            name=link.get("title", "").strip() or link.text.strip(),
                            slug=link["href"].strip("/").split("/")[-1],
                            artist_id=artist.id,
                        )
                    )
            return songs
        except Exception as e:
            self._logger.error(f"Error getting songs: {e}")
            return []

    async def get_song_details(
        self, artist: Artist, song: Song
    ) -> Optional[ScrapeResult]:
        """Get song details"""
        try:
            html = await self._get(f"{artist.url}{song.url}")
            soup = BeautifulSoup(html, "html.parser")

            views = 0
            if views_div := soup.find("div", class_="head-info-exib"):
                if views_text := views_div.find("b"):
                    views = int(views_text.text.replace(".", ""))

            if content_div := soup.find("div", class_="lyric-original"):
                paragraphs = []
                for p in content_div.find_all("p"):
                    lines = [element for element in p.stripped_strings]
                    paragraphs.append("\n".join(lines))
                content = "\n\n".join(paragraphs)
                return ScrapeResult(content=content, views=views)

            return None
        except Exception as e:
            self._logger.error(f"Error getting song details: {e}")
            return None

    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
