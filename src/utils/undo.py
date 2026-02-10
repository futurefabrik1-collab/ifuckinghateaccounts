"""
Persistent Undo History System

Manages undo/redo operations with persistent storage.
"""

import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from config import Config
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class UndoManager:
    """Manages undo history with persistent storage"""
    
    def __init__(self, statement_folder: Path):
        """
        Initialize undo manager
        
        Args:
            statement_folder: Path to statement folder
        """
        self.statement_folder = statement_folder
        self.undo_file = statement_folder / '.undo_history.json'
        self.redo_file = statement_folder / '.redo_history.json'
        
        self.undo_history = self._load_history(self.undo_file)
        self.redo_history = self._load_history(self.redo_file)
    
    def _load_history(self, file_path: Path) -> deque:
        """
        Load history from JSON file
        
        Args:
            file_path: Path to history file
        
        Returns:
            Deque containing history items
        """
        if not Config.UNDO_PERSIST:
            return deque(maxlen=Config.UNDO_HISTORY_SIZE)
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data)} items from {file_path.name}")
                    return deque(data, maxlen=Config.UNDO_HISTORY_SIZE)
            except Exception as e:
                logger.error(f"Failed to load history from {file_path}: {e}")
        
        return deque(maxlen=Config.UNDO_HISTORY_SIZE)
    
    def _save_history(self, file_path: Path, history: deque):
        """
        Save history to JSON file
        
        Args:
            file_path: Path to history file
            history: Deque to save
        """
        if not Config.UNDO_PERSIST:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(list(history), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(history)} items to {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to save history to {file_path}: {e}")
    
    def add_action(self, action: Dict):
        """
        Add an action to undo history
        
        Args:
            action: Action dictionary with type and details
        """
        # Add timestamp if not present
        if 'timestamp' not in action:
            action['timestamp'] = datetime.now().isoformat()
        
        # Add to undo history
        self.undo_history.append(action)
        self._save_history(self.undo_file, self.undo_history)
        
        # Clear redo history (new action invalidates redo)
        self.redo_history.clear()
        self._save_history(self.redo_file, self.redo_history)
        
        logger.debug(f"Added action to undo history: {action.get('type')}")
    
    def undo(self) -> Optional[Dict]:
        """
        Pop last action from undo history
        
        Returns:
            Last action, or None if history is empty
        """
        if len(self.undo_history) == 0:
            logger.debug("Undo history is empty")
            return None
        
        action = self.undo_history.pop()
        self._save_history(self.undo_file, self.undo_history)
        
        # Add to redo history
        self.redo_history.append(action)
        self._save_history(self.redo_file, self.redo_history)
        
        logger.info(f"Undid action: {action.get('type')}")
        
        return action
    
    def redo(self) -> Optional[Dict]:
        """
        Pop last action from redo history
        
        Returns:
            Last undone action, or None if redo history is empty
        """
        if len(self.redo_history) == 0:
            logger.debug("Redo history is empty")
            return None
        
        action = self.redo_history.pop()
        self._save_history(self.redo_file, self.redo_history)
        
        # Add back to undo history
        self.undo_history.append(action)
        self._save_history(self.undo_file, self.undo_history)
        
        logger.info(f"Redid action: {action.get('type')}")
        
        return action
    
    def get_undo_history(self) -> List[Dict]:
        """
        Get undo history as list
        
        Returns:
            List of undo actions (newest first)
        """
        return list(reversed(self.undo_history))
    
    def get_redo_history(self) -> List[Dict]:
        """
        Get redo history as list
        
        Returns:
            List of redo actions (newest first)
        """
        return list(reversed(self.redo_history))
    
    def clear(self):
        """Clear all history"""
        self.undo_history.clear()
        self.redo_history.clear()
        self._save_history(self.undo_file, self.undo_history)
        self._save_history(self.redo_file, self.redo_history)
        logger.info("Cleared undo/redo history")
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.undo_history) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.redo_history) > 0
