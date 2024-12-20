from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from letras.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_settings():
    with patch("letras.cli.Config.get_settings") as mock:
        settings = MagicMock()
        settings.db_host = "test-db"
        settings.db_port = 5432
        settings.db_name = "test"
        settings.db_user = "test"
        settings.db_password = "test"
        settings.base_url = "http://test.com"
        mock.return_value = settings
        yield settings


def test_full_command(runner, mock_settings, tmp_path):
    """Test full command execution"""
    with patch("letras.cli.FullRunner") as mock_runner_cls:
        # Setup mock runner
        mock_runner = MagicMock()
        mock_runner.initialize = AsyncMock()
        mock_runner.run = AsyncMock()
        mock_runner.close = AsyncMock()
        mock_runner_cls.return_value = mock_runner

        # Execute command
        result = runner.invoke(cli, ["full", "--output", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        mock_runner_cls.assert_called_once()
        assert mock_runner.initialize.await_count == 1
        assert mock_runner.run.await_count == 1
        assert mock_runner.close.await_count == 1
        mock_runner.run.assert_awaited_with(output_dir=str(tmp_path))


def test_incremental_command(runner, mock_settings, tmp_path):
    """Test incremental command execution"""
    with patch("letras.cli.IncrementalRunner") as mock_runner_cls:
        # Setup mock runner
        mock_runner = MagicMock()
        mock_runner.initialize = AsyncMock()
        mock_runner.run = AsyncMock()
        mock_runner.close = AsyncMock()
        mock_runner_cls.return_value = mock_runner

        # Execute command
        result = runner.invoke(cli, ["incremental", "--output", str(tmp_path)])

        # Verify
        assert result.exit_code == 0
        mock_runner_cls.assert_called_once()
        assert mock_runner.initialize.await_count == 1
        assert mock_runner.run.await_count == 1
        assert mock_runner.close.await_count == 1
        mock_runner.run.assert_awaited_with(output_dir=str(tmp_path))


def test_init_command(runner, mock_settings):
    """Test init command execution"""
    with patch("letras.cli.PostgresConnection") as mock_db_cls:
        # Setup mock database
        mock_db = MagicMock()
        mock_db.initialize = AsyncMock()
        mock_db.close = AsyncMock()
        mock_db_cls.return_value = mock_db

        # Execute command
        result = runner.invoke(cli, ["init"])

        # Verify
        assert result.exit_code == 0
        mock_db_cls.assert_called_once()
        assert mock_db.initialize.await_count == 1
        assert mock_db.close.await_count == 1


def test_full_command_error(runner, mock_settings):
    """Test error handling in full command"""
    with patch("letras.cli.FullRunner") as mock_runner_cls:
        # Setup mock to raise exception
        mock_runner = MagicMock()
        mock_runner.initialize = AsyncMock(side_effect=Exception("Test error"))
        mock_runner.close = AsyncMock()
        mock_runner_cls.return_value = mock_runner

        # Execute command
        result = runner.invoke(cli, ["full"])

        # Verify
        assert result.exit_code != 0
        assert "Test error" in result.output
        assert mock_runner.close.await_count == 1


def test_init_command_error(runner, mock_settings):
    """Test error handling in init command"""
    with patch("letras.cli.PostgresConnection") as mock_db_cls:
        # Setup mock to raise exception
        mock_db = MagicMock()
        mock_db.initialize = AsyncMock(side_effect=Exception("DB Error"))
        mock_db.close = AsyncMock()
        mock_db_cls.return_value = mock_db

        # Execute command
        result = runner.invoke(cli, ["init"])

        # Verify
        assert result.exit_code != 0
        assert "DB Error" in result.output
        assert mock_db.close.await_count == 1


def test_output_dir_creation(runner, mock_settings, tmp_path):
    """Test output directory creation"""
    output_dir = tmp_path / "test_output"

    with patch("letras.cli.FullRunner") as mock_runner_cls:
        # Setup mock runner
        mock_runner = MagicMock()
        mock_runner.initialize = AsyncMock()
        mock_runner.run = AsyncMock()
        mock_runner.close = AsyncMock()
        mock_runner_cls.return_value = mock_runner

        # Execute command
        runner.invoke(cli, ["full", "--output", str(output_dir)])

        # Verify
        assert output_dir.exists()
        assert output_dir.is_dir()
