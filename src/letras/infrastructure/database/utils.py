import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path


class PostgresUtils:
    """Utilities for PostgreSQL backup and restore operations"""

    def __init__(self, db_config: dict):
        """
        Initialize PostgreSQL utilities
        
        Args:
            db_config: Database configuration dictionary with host, port, database,
                      user, and password
        """
        self.db_config = db_config
        self._logger = logging.getLogger(__name__)

    async def create_backup(self, output_dir: str) -> str:
        """
        Create a PostgreSQL backup file
        
        Args:
            output_dir: Directory to store the backup file
            
        Returns:
            str: Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"letras-{timestamp}.sql"
        output_path = Path(output_dir) / filename
        
        # Set environment variables for pg_dump
        env = os.environ.copy()
        env.update({
            'PGHOST': self.db_config['host'],
            'PGPORT': str(self.db_config['port']),
            'PGDATABASE': self.db_config['database'],
            'PGUSER': self.db_config['user'],
            'PGPASSWORD': self.db_config['password']
        })
        
        # Create backup using pg_dump
        try:
            self._logger.info(f"Creating database backup to {output_path}")
            
            process = await asyncio.create_subprocess_exec(
                'pg_dump',
                '--clean',  # Clean (drop) database objects before recreating
                '--if-exists',  # Add IF EXISTS clauses
                '--no-owner',  # Don't output commands to set ownership
                '--no-privileges',  # Don't output privileges
                '-F', 'p',  # Plain-text SQL script
                '-f', str(output_path),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Backup failed: {stderr.decode()}")
                
            self._logger.info("Database backup completed successfully")
            return str(output_path)
            
        except Exception as e:
            self._logger.error(f"Error creating backup: {str(e)}")
            raise
    
    async def restore_backup(self, backup_file: str) -> None:
        """
        Restore a PostgreSQL backup file
        
        Args:
            backup_file: Path to the backup file to restore
        """
        if not os.path.exists(backup_file):
            raise Exception(f"Backup file not found: {backup_file}")
            
        # Set environment variables for psql
        env = os.environ.copy()
        env.update({
            'PGHOST': self.db_config['host'],
            'PGPORT': str(self.db_config['port']),
            'PGDATABASE': self.db_config['database'],
            'PGUSER': self.db_config['user'],
            'PGPASSWORD': self.db_config['password']
        })
        
        try:
            self._logger.info(f"Restoring database from {backup_file}")
            
            process = await asyncio.create_subprocess_exec(
                'psql',
                '-f', backup_file,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Restore failed: {stderr.decode()}")
                
            self._logger.info("Database restore completed successfully")
                
        except Exception as e:
            self._logger.error(f"Error restoring backup: {str(e)}")
            raise