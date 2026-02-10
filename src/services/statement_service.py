"""
Statement Service - Business Logic Layer

Handles all statement-related operations separate from web layer.
"""

import pandas as pd
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from werkzeug.datastructures import FileStorage

from config import Config
from src.utils.logging import setup_logger
from src.utils.security import (
    validate_file_upload, 
    validate_path_traversal,
    validate_statement_name,
    validate_row_number,
    sanitize_filename
)
from src.utils.backup import BackupManager
from src.utils.undo import UndoManager

logger = setup_logger(__name__)


class StatementService:
    """Service for managing bank statements"""
    
    def __init__(self, base_dir: Path):
        """
        Initialize statement service
        
        Args:
            base_dir: Base directory for statements
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_statement_folder(self, statement_name: str) -> Path:
        """Get folder for a specific statement"""
        statement_name = validate_statement_name(statement_name)
        folder_name = statement_name.rsplit('.', 1)[0]
        return self.base_dir / folder_name
    
    def _get_receipts_folder(self, statement_name: str, subfolder: str = 'receipts') -> Path:
        """Get receipts subfolder for a statement"""
        return self._get_statement_folder(statement_name) / subfolder
    
    def _create_statement_folders(self, statement_name: str) -> Dict[str, Path]:
        """Create all necessary folders for a statement"""
        statement_folder = self._get_statement_folder(statement_name)
        receipts_folder = statement_folder / 'receipts'
        matched_folder = statement_folder / 'matched_receipts'
        
        statement_folder.mkdir(parents=True, exist_ok=True)
        receipts_folder.mkdir(parents=True, exist_ok=True)
        matched_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created folders for statement: {statement_name}")
        
        return {
            'base': statement_folder,
            'receipts': receipts_folder,
            'matched': matched_folder
        }
    
    def upload_statement(self, file: FileStorage) -> Dict:
        """
        Upload a new bank statement
        
        Args:
            file: Uploaded file
        
        Returns:
            Dictionary with upload results
        
        Raises:
            ValueError: If validation fails
        """
        # Validate file
        safe_filename, file_size = validate_file_upload(
            file, 
            Config.ALLOWED_STATEMENT_EXTENSIONS
        )
        
        # Create folders
        folders = self._create_statement_folders(safe_filename)
        
        # Save file
        filepath = folders['base'] / safe_filename
        file.save(str(filepath))
        
        logger.info(f"Uploaded statement: {safe_filename} ({file_size} bytes)")
        
        return {
            'success': True,
            'filename': safe_filename,
            'size': file_size,
            'message': f'Statement uploaded: {safe_filename}',
            'folders': {
                'receipts': str(folders['receipts'].relative_to(self.base_dir.parent)),
                'matched': str(folders['matched'].relative_to(self.base_dir.parent))
            }
        }
    
    def load_statement_csv(
        self, 
        statement_name: str, 
        create_if_missing: bool = False
    ) -> pd.DataFrame:
        """
        Load statement CSV with match data
        
        Args:
            statement_name: Statement filename
            create_if_missing: Create match columns if they don't exist
        
        Returns:
            DataFrame with statement data
        
        Raises:
            FileNotFoundError: If statement doesn't exist
        """
        statement_name = validate_statement_name(statement_name)
        
        statement_folder = self._get_statement_folder(statement_name)
        statement_file = statement_folder / statement_name
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        # Validate paths
        validate_path_traversal(self.base_dir, statement_file)
        
        # Load from output if exists, otherwise from original
        if output_csv.exists():
            df = pd.read_csv(
                output_csv, 
                sep=';', 
                encoding='utf-8-sig',
                dtype={'Matched Receipt File': str}
            )
            logger.debug(f"Loaded matches CSV: {output_csv.name}")
        elif statement_file.exists():
            df = pd.read_csv(statement_file, sep=';', encoding='utf-8-sig')
            
            if create_if_missing:
                # Initialize match columns
                if 'Matching Receipt Found' not in df.columns:
                    df['Matching Receipt Found'] = False
                    df['Matched Receipt File'] = ''
                    df['Match Confidence'] = 0
                if 'No Receipt Needed' not in df.columns:
                    df['No Receipt Needed'] = False
                if 'Owner_Mark' not in df.columns:
                    df['Owner_Mark'] = False
                if 'Owner_Flo' not in df.columns:
                    df['Owner_Flo'] = False
                
                logger.debug(f"Loaded original CSV and added match columns: {statement_file.name}")
        else:
            raise FileNotFoundError(f"Statement not found: {statement_name}")
        
        return df
    
    def save_statement_csv(
        self, 
        statement_name: str, 
        df: pd.DataFrame,
        create_backup: bool = True
    ):
        """
        Save statement CSV with automatic backup
        
        Args:
            statement_name: Statement filename
            df: DataFrame to save
            create_backup: Whether to create backup before saving
        """
        statement_name = validate_statement_name(statement_name)
        
        statement_folder = self._get_statement_folder(statement_name)
        output_csv = statement_folder / f"{statement_name.rsplit('.', 1)[0]}_matches.csv"
        
        # Validate path
        validate_path_traversal(self.base_dir, output_csv)
        
        # Create backup if requested
        if create_backup:
            backup_manager = BackupManager(statement_folder)
            backup_manager.create_backup(output_csv)
        
        # Save CSV
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, sep=';', index=False, encoding='utf-8-sig')
        
        logger.info(f"Saved statement CSV: {output_csv.name}")
    
    def get_all_statements(self) -> List[Dict]:
        """
        Get list of all statements
        
        Returns:
            List of statement information dictionaries
        """
        from datetime import datetime
        
        statements = []
        
        for folder in self.base_dir.iterdir():
            if not folder.is_dir():
                continue
            
            # Look for CSV/Excel files
            for ext in Config.ALLOWED_STATEMENT_EXTENSIONS:
                for statement_file in folder.glob(f"*.{ext}"):
                    # Skip backup and match files
                    if statement_file.stem.endswith('_matches') or '_backup' in statement_file.stem:
                        continue
                    
                    statements.append({
                        'name': statement_file.name,
                        'folder': folder.name,
                        'path': str(statement_file.relative_to(self.base_dir.parent)),
                        'modified': datetime.fromtimestamp(
                            statement_file.stat().st_mtime
                        ).isoformat(),
                        'size': statement_file.stat().st_size,
                        'receipts_folder': str(
                            (folder / 'receipts').relative_to(self.base_dir.parent)
                        ),
                        'matched_folder': str(
                            (folder / 'matched_receipts').relative_to(self.base_dir.parent)
                        )
                    })
        
        # Sort by modification date (newest first)
        statements.sort(key=lambda x: x['modified'], reverse=True)
        
        logger.debug(f"Found {len(statements)} statement(s)")
        
        return statements
    
    def get_summary_stats(self, statement_name: str) -> Dict:
        """
        Calculate summary statistics for a statement
        
        Args:
            statement_name: Statement filename
        
        Returns:
            Dictionary with statistics
        """
        df = self.load_statement_csv(statement_name)
        
        total = int(len(df))
        matched = int(df['Matching Receipt Found'].sum()) if 'Matching Receipt Found' in df.columns else 0
        no_receipt_needed = int(df['No Receipt Needed'].sum()) if 'No Receipt Needed' in df.columns else 0
        completed = matched + no_receipt_needed
        missing = total - completed
        completion_rate = float((completed / total * 100) if total > 0 else 0)
        
        # Count receipts in folders
        receipts_folder = self._get_receipts_folder(statement_name, 'receipts')
        matched_folder = self._get_receipts_folder(statement_name, 'matched_receipts')
        
        receipts_in_folder = len(list(receipts_folder.glob("*.pdf"))) if receipts_folder.exists() else 0
        receipts_renamed = len(list(matched_folder.glob("*.pdf"))) if matched_folder.exists() else 0
        
        return {
            'total': total,
            'matched': matched,
            'no_receipt_needed': no_receipt_needed,
            'completed': completed,
            'missing': missing,
            'completion_rate': round(completion_rate, 1),
            'receipts_in_folder': receipts_in_folder,
            'receipts_renamed': receipts_renamed
        }
    
    def delete_statement(self, statement_name: str) -> Dict:
        """
        Delete a statement and all associated data
        
        Args:
            statement_name: Statement filename
        
        Returns:
            Dictionary with deletion results
        """
        statement_name = validate_statement_name(statement_name)
        statement_folder = self._get_statement_folder(statement_name)
        
        # Validate path
        validate_path_traversal(self.base_dir, statement_folder)
        
        if not statement_folder.exists():
            raise FileNotFoundError(f"Statement not found: {statement_name}")
        
        # Delete entire folder
        shutil.rmtree(statement_folder)
        
        logger.info(f"Deleted statement: {statement_name}")
        
        return {
            'success': True,
            'message': f'Statement deleted: {statement_name}'
        }
