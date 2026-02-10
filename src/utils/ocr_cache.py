"""
OCR Caching System

Caches extracted text from receipts to avoid expensive re-processing.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from config import Config
from src.utils.logging import setup_logger

logger = setup_logger(__name__)


class OCRCache:
    """Manages OCR result caching"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize OCR cache
        
        Args:
            cache_dir: Directory for cache files (uses config default if None)
        """
        self.cache_dir = cache_dir or Config.OCR_CACHE_DIR
        self.cache_enabled = Config.OCR_CACHE_ENABLED
        
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.index_file = self.cache_dir / 'cache_index.json'
            self.index = self._load_index()
        else:
            self.index = {}
    
    def _load_index(self) -> Dict:
        """
        Load cache index from disk
        
        Returns:
            Cache index dictionary
        """
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                    logger.info(f"Loaded OCR cache index with {len(index)} entries")
                    return index
            except Exception as e:
                logger.error(f"Failed to load cache index: {e}")
        
        return {}
    
    def _save_index(self):
        """Save cache index to disk"""
        if not self.cache_enabled:
            return
        
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
            logger.debug(f"Saved cache index with {len(self.index)} entries")
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """
        Generate hash of file for cache key
        
        Args:
            file_path: Path to file
        
        Returns:
            MD5 hash of file contents
        """
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def get(self, file_path: Path) -> Optional[Dict]:
        """
        Get cached OCR result for file
        
        Args:
            file_path: Path to receipt file
        
        Returns:
            Cached OCR data, or None if not in cache
        """
        if not self.cache_enabled:
            return None
        
        try:
            file_hash = self._get_file_hash(file_path)
            
            if file_hash in self.index:
                cache_entry = self.index[file_hash]
                cache_file = self.cache_dir / f"{file_hash}.json"
                
                if cache_file.exists():
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    logger.debug(f"Cache hit for {file_path.name}")
                    
                    # Update last accessed time
                    cache_entry['last_accessed'] = datetime.now().isoformat()
                    cache_entry['access_count'] = cache_entry.get('access_count', 0) + 1
                    self._save_index()
                    
                    return cached_data
                else:
                    # Cache file missing - remove from index
                    logger.warning(f"Cache file missing for {file_hash}, removing from index")
                    del self.index[file_hash]
                    self._save_index()
            
            logger.debug(f"Cache miss for {file_path.name}")
            return None
            
        except Exception as e:
            logger.error(f"Error reading cache for {file_path}: {e}")
            return None
    
    def set(self, file_path: Path, ocr_data: Dict):
        """
        Store OCR result in cache
        
        Args:
            file_path: Path to receipt file
            ocr_data: OCR extraction results
        """
        if not self.cache_enabled:
            return
        
        try:
            file_hash = self._get_file_hash(file_path)
            cache_file = self.cache_dir / f"{file_hash}.json"
            
            # Save OCR data
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(ocr_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Update index
            self.index[file_hash] = {
                'filename': file_path.name,
                'file_size': file_path.stat().st_size,
                'cached_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'access_count': 0
            }
            self._save_index()
            
            logger.debug(f"Cached OCR result for {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error caching OCR result for {file_path}: {e}")
    
    def invalidate(self, file_path: Path):
        """
        Remove file from cache
        
        Args:
            file_path: Path to receipt file
        """
        if not self.cache_enabled:
            return
        
        try:
            file_hash = self._get_file_hash(file_path)
            
            if file_hash in self.index:
                cache_file = self.cache_dir / f"{file_hash}.json"
                
                if cache_file.exists():
                    cache_file.unlink()
                
                del self.index[file_hash]
                self._save_index()
                
                logger.info(f"Invalidated cache for {file_path.name}")
        
        except Exception as e:
            logger.error(f"Error invalidating cache for {file_path}: {e}")
    
    def clear(self):
        """Clear entire cache"""
        if not self.cache_enabled:
            return
        
        try:
            # Remove all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "cache_index.json":
                    cache_file.unlink()
            
            # Clear index
            self.index.clear()
            self._save_index()
            
            logger.info("Cleared OCR cache")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        if not self.cache_enabled:
            return {'enabled': False}
        
        total_entries = len(self.index)
        total_size = sum(
            (self.cache_dir / f"{hash}.json").stat().st_size
            for hash, entry in self.index.items()
            if (self.cache_dir / f"{hash}.json").exists()
        )
        
        total_accesses = sum(entry.get('access_count', 0) for entry in self.index.values())
        
        return {
            'enabled': True,
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_accesses': total_accesses,
            'cache_dir': str(self.cache_dir)
        }
