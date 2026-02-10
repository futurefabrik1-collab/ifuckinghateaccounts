"""
Automated Backup System

Handles automatic backups of statement files before modifications.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import Config
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class BackupManager:
    """Manages automated backups of statement files"""
    
    def __init__(self, statement_folder: Path):
        """
        Initialize backup manager
        
        Args:
            statement_folder: Path to statement folder
        """
        self.statement_folder = statement_folder
        self.backup_folder = statement_folder / 'backups'
        
        if Config.BACKUP_ENABLED:
            self.backup_folder.mkdir(exist_ok=True)
    
    def create_backup(self, file_path: Path, suffix: str = "") -> Optional[Path]:
        """
        Create a timestamped backup of a file
        
        Args:
            file_path: Path to file to backup
            suffix: Optional suffix to add to backup filename
        
        Returns:
            Path to backup file, or None if backups disabled or file doesn't exist
        """
        if not Config.BACKUP_ENABLED:
            logger.debug("Backups disabled - skipping")
            return None
        
        if not file_path.exists():
            logger.debug(f"File {file_path} doesn't exist - no backup needed")
            return None
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = file_path.stem
        extension = file_path.suffix
        
        backup_name = f"{base_name}_backup_{timestamp}"
        if suffix:
            backup_name += f"_{suffix}"
        backup_name += extension
        
        backup_path = self.backup_folder / backup_name
        
        # Create backup
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path.name}")
            
            # Clean old backups
            self._cleanup_old_backups(base_name, extension)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _cleanup_old_backups(self, base_name: str, extension: str):
        """
        Remove old backups beyond retention limit
        
        Args:
            base_name: Base filename to match
            extension: File extension to match
        """
        try:
            # Find all backups for this file
            pattern = f"{base_name}_backup_*{extension}"
            backups = sorted(self.backup_folder.glob(pattern))
            
            # Remove oldest backups if over limit
            if len(backups) > Config.BACKUP_RETENTION_COUNT:
                to_remove = backups[:-Config.BACKUP_RETENTION_COUNT]
                for old_backup in to_remove:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup.name}")
                
                logger.info(f"Cleaned up {len(to_remove)} old backup(s)")
        
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """
        Restore a backup file
        
        Args:
            backup_path: Path to backup file
            target_path: Path to restore to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current file before restoring
            if target_path.exists():
                self.create_backup(target_path, suffix="pre_restore")
            
            # Restore
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored backup: {backup_path.name} -> {target_path.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self, base_name: Optional[str] = None) -> list:
        """
        List available backups
        
        Args:
            base_name: Optional base filename to filter by
        
        Returns:
            List of backup file paths, sorted by date (newest first)
        """
        if not self.backup_folder.exists():
            return []
        
        pattern = f"{base_name}_backup_*" if base_name else "*_backup_*"
        backups = sorted(
            self.backup_folder.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        return backups
