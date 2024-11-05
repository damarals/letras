import pytest
import shutil
from unittest.mock import Mock, patch

@pytest.fixture
def mock_config():
    """Mock configuration"""
    return {
        'base_url': 'https://mock.url'
    }

@pytest.fixture
def mock_db():
    """Mock database connection"""
    mock_conn = Mock()
    mock_conn.execute.return_value.fetchone.return_value = [1]  # Default return for ID queries
    mock_conn.execute.return_value.fetchall.return_value = []  # Default empty list for other queries
    return mock_conn

@pytest.fixture
def mock_config_file(tmp_path, mock_config):
    """Create a temporary config file"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    
    return config_file

@pytest.fixture
def runner(tmp_path, mock_config_file, mock_db):
    """Setup test runner with mocked configuration"""
    with patch('core.utils.Path') as mock_path:
        # Make the config loader find our mock config file
        mock_path.return_value = mock_config_file
        
        from core.runner import GospelLyricsRunner
        
        runner = GospelLyricsRunner()
        runner.data_dir = tmp_path / "data"
        runner.temp_dir = runner.data_dir / "temp"
        runner.data_dir.mkdir(exist_ok=True)
        runner.temp_dir.mkdir(exist_ok=True)
        runner.conn = mock_db
        
        yield runner
        
        # Cleanup
        shutil.rmtree(runner.temp_dir, ignore_errors=True)