import requests
import polars as pl
from bs4 import BeautifulSoup

from core.utils import load_config

def get_artists() -> pl.DataFrame:
    """
    Scrapes gospel artists data and returns a Polars DataFrame with names and URLs.
    
    Returns:
    --------
    pl.DataFrame
        DataFrame containing artist names and slugs
    """
    try:
        config = load_config()
        response = requests.get(f'{config.base_url}/estilos/gospelreligioso/todosartistas.html')
        soup = BeautifulSoup(response.text, 'html.parser')
        
        artists_data = [
            {
                'name': link.text.strip(),
                'slug': link['href'].replace('/','')
            }
            for link in soup.find_all('a')
        ]
        
        return pl.DataFrame(artists_data)
    
    except Exception as e:
        raise Exception(f"Error scraping artists data: {str(e)}")
    
def extract_artist_views(soup: BeautifulSoup) -> int:
    """
    Extract artist's view count from the page.
    
    Parameters:
    -----------
    soup : BeautifulSoup
        Parsed HTML content
    
    Returns:
    --------
    int
        Number of views, or 0 if not found
    """
    try:
        views_div = soup.find('div', class_='head-info-exib')
        if views_div:
            views_text = views_div.find('b').text.strip()
            # Remove pontos e converte para inteiro
            views = int(views_text.replace('.', ''))
            return views
    except Exception:
        pass
    return 0

def _extract_songs_from_default(soup: BeautifulSoup) -> list:
    """
    Extract songs from the default artist page layout.
    
    Parameters:
    -----------
    soup : BeautifulSoup
        Parsed HTML content
    
    Returns:
    --------
    list
        List of dictionaries containing song info
    """
    songs_div = soup.find('div', class_='artista-todas')
    if not songs_div:
        return []
            
    songs = []
    for song in songs_div.find_all('li', class_='songList-table-row'):
        link = song.find('a', class_='songList-table-songName')
        if link:
            name = link.text.strip()
            song_slug = link['href'].strip('/').split('/')[-1]
            songs.append({
                'name': name,
                'slug': song_slug
            })
            
    return songs

def _extract_songs_from_top_songs(soup: BeautifulSoup) -> list:
    """
    Extract songs from the top songs layout (alternative layout).
    
    Parameters:
    -----------
    soup : BeautifulSoup
        Parsed HTML content
    
    Returns:
    --------
    list
        List of dictionaries containing song info
    """
    songs_div = soup.find('div', class_='artistTopSongs')
    if not songs_div:
        return []
            
    songs = []
    for song in songs_div.find_all('li', class_='songList-table-row'):
        link = song.find('a')
        if link:
            name = link.get('title', '').strip() or link.text.strip()
            href = link.get('href', '').strip('/')
            if href:
                song_slug = href.split('/')[-1]
                songs.append({
                    'name': name,
                    'slug': song_slug
                })
                
    return songs

def get_artist_songs(artist_slug: str) -> pl.DataFrame:
    """
    Scrapes all songs from a specific artist using their slug.
    
    Parameters:
    -----------
    artist_slug : str
        The artist's slug
    
    Returns:
    --------
    pl.DataFrame
        DataFrame containing artist song names and slugs
    
    Raises:
    -------
    Exception
        If no songs are found or if there's an error during scraping
    """
    try:
        config = load_config()
        response = requests.get(f"{config.base_url}/{artist_slug}/")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try default layout first
        songs = _extract_songs_from_default(soup)
        
        # If no songs found, try alternative layout
        if not songs:
            songs = _extract_songs_from_top_songs(soup)
            
        if not songs:
            raise Exception("No songs found")
            
        return pl.DataFrame(songs)
    
    except Exception as e:
        raise Exception(f"Error scraping songs: {str(e)}")


def get_artist_song_lyrics(artist_slug: str, song_slug: str) -> str:
    """
    Scrapes the lyrics of a specific song from an artist.
    
    Parameters:
    -----------
    artist_slug : str
        The artist's slug
    song_slug : str
        The song's slug
    
    Returns:
    --------
    str
        The song lyrics with paragraphs separated by newlines
    """
    try:
        config = load_config()
        url = f"{config.base_url}/{artist_slug}/{song_slug}/"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the lyrics container
        lyrics_div = soup.find('div', class_='lyric-original')
        if not lyrics_div:
            raise Exception("Couldn't find lyrics container")
        
        # Process each paragraph
        paragraphs = []
        for p in lyrics_div.find_all('p'):
            # Get all text from paragraph, including marked annotations
            lines = []
            for element in p.stripped_strings:
                lines.append(element)
            # Join lines with line breaks and add to paragraphs
            paragraphs.append('\n'.join(lines))
        
        # Join paragraphs with double line breaks
        lyrics = '\n\n'.join(paragraphs)
        
        if not lyrics.strip():
            raise Exception("No lyrics found")
            
        return lyrics
    
    except Exception as e:
        raise Exception(f"Error scraping lyrics: {str(e)}")