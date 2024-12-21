import asyncio
from pathlib import Path
import pytest

from letras.infrastructure.database.utils import PostgresUtils


@pytest.fixture
async def db_config(request):
    """Test database config using Docker service"""
    return {
        "host": "db",  # Use docker service name
        "port": 5432,
        "database": "letras",
        "user": "letras",
        "password": "letras",
    }


@pytest.fixture
async def postgres_utils(db_config):
    return PostgresUtils(db_config)


@pytest.mark.asyncio
async def test_backup_and_restore_cycle(postgres_utils, tmp_path):
    """Test full backup and restore cycle"""
    backup_file = None
    try:
        # Create a backup
        backup_file = await postgres_utils.create_backup(str(tmp_path))
        
        # Verify backup was created
        assert Path(backup_file).exists()
        assert Path(backup_file).stat().st_size > 0
        
        # Save current table counts
        original_counts = await get_table_counts(postgres_utils.db_config)
        
        # Drop all data
        await drop_all_data(postgres_utils.db_config)
        
        # Verify tables are empty
        empty_counts = await get_table_counts(postgres_utils.db_config)
        assert all(count == 0 for count in empty_counts.values())
        
        # Restore from backup
        await postgres_utils.restore_backup(backup_file)
        
        # Verify data was restored
        restored_counts = await get_table_counts(postgres_utils.db_config)
        assert restored_counts == original_counts
        
    finally:
        # Cleanup
        if backup_file and Path(backup_file).exists():
            Path(backup_file).unlink()


@pytest.mark.asyncio
async def test_backup_file_format(postgres_utils, tmp_path):
    """Test backup file format and content"""
    backup_file = None
    try:
        backup_file = await postgres_utils.create_backup(str(tmp_path))
        
        # Verify file exists and has .sql extension
        assert Path(backup_file).exists()
        assert backup_file.endswith('.sql')
        
        # Read content and verify basic SQL structure
        content = Path(backup_file).read_text()
        assert 'CREATE TABLE' in content
        assert 'artists' in content
        assert 'songs' in content
        assert 'lyrics' in content
    
    finally:
        if backup_file and Path(backup_file).exists():
            Path(backup_file).unlink()


async def get_table_counts(db_config: dict) -> dict:
    """Get record counts for all tables"""
    env = {
        'PGHOST': db_config['host'],
        'PGPORT': str(db_config['port']),
        'PGDATABASE': db_config['database'],
        'PGUSER': db_config['user'],
        'PGPASSWORD': db_config['password']
    }
    
    tables = ['artists', 'songs', 'lyrics']
    counts = {}
    
    for table in tables:
        process = await asyncio.create_subprocess_exec(
            'psql',
            '-t',  # Tuple only output
            '-A',  # Unaligned table output
            '-c', f'SELECT COUNT(*) FROM {table}',
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, _ = await process.communicate()
        counts[table] = int(stdout.decode().strip() or 0)
    
    return counts


async def drop_all_data(db_config: dict):
    """Drop all data from tables"""
    env = {
        'PGHOST': db_config['host'],
        'PGPORT': str(db_config['port']),
        'PGDATABASE': db_config['database'],
        'PGUSER': db_config['user'],
        'PGPASSWORD': db_config['password']
    }
    
    process = await asyncio.create_subprocess_exec(
        'psql',
        '-c', 'TRUNCATE lyrics, songs, artists CASCADE',
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await process.communicate()