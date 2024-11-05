from unittest.mock import patch
import polars as pl

def test_collect_all_songs_new_artists(runner):
    """Test collecting songs from new artists"""
    # Mock artist data
    mock_artists_df = pl.DataFrame({
        'name': ['Artist 1', 'Artist 2'],
        'slug': ['artist-1', 'artist-2']
    })
    
    # Mock song data
    mock_songs_df = pl.DataFrame({
        'name': ['Song 1', 'Song 2'],
        'slug': ['song-1', 'song-2']
    })
    
    # Mock the requests for artist views
    def mock_get(*args, **kwargs):
        class MockResponse:
            @property
            def text(self):
                return '<div class="head-info-exib"><b>1.000</b></div>'
        return MockResponse()
    
    with patch('core.runner.get_artists', return_value=mock_artists_df), \
         patch('core.runner.get_artist_songs', return_value=mock_songs_df), \
         patch('requests.get', side_effect=mock_get):
        
        result = runner.collect_all_songs()
        
        assert not result.is_empty()
        assert len(result) == 4  # 2 songs per artist
        assert 'artist_name' in result.columns
        assert 'artist_id' in result.columns

def test_get_artist_views(runner):
    """Test getting artist views"""
    mock_html = """
        <div class="head-info-exib">
            <b>1.234</b>
        </div>
    """
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = mock_html
        views = runner.get_artist_views('artist-slug')
        
        assert views == 1234
        mock_get.assert_called_once_with(f"{runner.config.base_url}artist-slug")

def test_process_song_success(runner):
    """Test successful song processing"""
    song_data = {
        'artist_name': 'João Silva',
        'artist_id': 1,
        'name': 'Música Teste',	
        'slug': 'musica-teste',
        'artist_slug': 'joao-silva'
    }
    
    mock_lyrics = """
O Senhor é o meu pastor, nada vai me faltar
Em verdes pastos me faz descansar,
Em águas calmas me guiará,
Minha alma ele vem restaurar
"""
    
    with patch('core.runner.get_artist_song_lyrics', return_value=mock_lyrics):
        success = runner.process_song(song_data)
        
        assert success
        # Verify database calls
        assert runner.conn.execute.call_count >= 2
        # Verify file creation
        expected_file = runner.temp_dir / "Joao Silva - Musica Teste.txt"
        assert expected_file.exists()

def test_process_song_no_lyrics(runner):
    """Test song processing when no lyrics are found"""
    song_data = {
        'artist_name': 'João Silva',
        'artist_id': 1,
        'name': 'Música Teste',	
        'slug': 'musica-teste',
        'artist_slug': 'joao-silva'
    }
    
    with patch('core.runner.get_artist_song_lyrics', return_value=None):
        success = runner.process_song(song_data)
        assert not success

def test_create_release_notes(runner):
    """Test creation of release notes"""
    test_data = pl.DataFrame({
        'artist_name': ['Artist 1', 'Artist 2'],
        'name': ['Song 1', 'Song 2'],
        'artist_views': [1000, 2000],
        'artist_id': [1, 2],
        'slug': ['song-1', 'song-2']
    })
    
    notes = runner.create_release_notes(test_data)
    assert isinstance(notes, str)
    assert 'Artist 1' in notes
    assert 'Artist 2' in notes
    assert 'Song 1' in notes
    assert 'Song 2' in notes