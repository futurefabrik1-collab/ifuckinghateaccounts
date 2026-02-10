"""
Monitoring and Health Check Utilities

Provides health checks and performance monitoring.
"""

import time
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from functools import wraps

from config import Config
from src.utils.logging import setup_logger

logger = setup_logger(__name__)

# Store app start time
APP_START_TIME = datetime.now()


def get_uptime() -> Dict:
    """
    Get application uptime
    
    Returns:
        Dictionary with uptime information
    """
    uptime_seconds = (datetime.now() - APP_START_TIME).total_seconds()
    
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    return {
        'seconds': int(uptime_seconds),
        'formatted': f"{hours}h {minutes}m {seconds}s",
        'started_at': APP_START_TIME.isoformat()
    }


def get_disk_usage(path: Optional[Path] = None) -> Dict:
    """
    Get disk usage for a path
    
    Args:
        path: Path to check (uses base dir if None)
    
    Returns:
        Dictionary with disk usage info
    """
    path = path or Config.BASE_DIR
    
    try:
        usage = psutil.disk_usage(str(path))
        
        return {
            'total_bytes': usage.total,
            'used_bytes': usage.used,
            'free_bytes': usage.free,
            'total_gb': round(usage.total / (1024**3), 2),
            'used_gb': round(usage.used / (1024**3), 2),
            'free_gb': round(usage.free / (1024**3), 2),
            'percent_used': usage.percent
        }
    except Exception as e:
        logger.error(f"Failed to get disk usage: {e}")
        return {'error': str(e)}


def get_memory_usage() -> Dict:
    """
    Get current memory usage
    
    Returns:
        Dictionary with memory usage info
    """
    try:
        memory = psutil.virtual_memory()
        
        return {
            'total_bytes': memory.total,
            'available_bytes': memory.available,
            'used_bytes': memory.used,
            'total_mb': round(memory.total / (1024**2), 2),
            'available_mb': round(memory.available / (1024**2), 2),
            'used_mb': round(memory.used / (1024**2), 2),
            'percent_used': memory.percent
        }
    except Exception as e:
        logger.error(f"Failed to get memory usage: {e}")
        return {'error': str(e)}


def get_health_status() -> Dict:
    """
    Get overall health status
    
    Returns:
        Dictionary with health check results
    """
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check disk space
    disk = get_disk_usage()
    if 'error' not in disk:
        if disk['percent_used'] > 90:
            health['status'] = 'degraded'
            health['checks']['disk'] = 'warning - low disk space'
        elif disk['percent_used'] > 95:
            health['status'] = 'unhealthy'
            health['checks']['disk'] = 'critical - very low disk space'
        else:
            health['checks']['disk'] = 'ok'
    else:
        health['checks']['disk'] = 'unknown'
    
    # Check memory
    memory = get_memory_usage()
    if 'error' not in memory:
        if memory['percent_used'] > 90:
            health['status'] = 'degraded'
            health['checks']['memory'] = 'warning - high memory usage'
        else:
            health['checks']['memory'] = 'ok'
    else:
        health['checks']['memory'] = 'unknown'
    
    # Check base directories exist
    if not Config.STATEMENTS_FOLDER.exists():
        health['status'] = 'unhealthy'
        health['checks']['statements_folder'] = 'missing'
    else:
        health['checks']['statements_folder'] = 'ok'
    
    # Check log directory
    if not Config.LOG_FILE.parent.exists():
        health['status'] = 'degraded'
        health['checks']['log_directory'] = 'missing'
    else:
        health['checks']['log_directory'] = 'ok'
    
    return health


def monitor_performance(func):
    """
    Decorator to monitor function performance
    
    Args:
        func: Function to monitor
    
    Returns:
        Wrapped function with performance logging
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            logger.info(f"{func.__name__} completed in {elapsed:.2f}s")
            
            # Log warning if slow
            if elapsed > 5.0:
                logger.warning(f"{func.__name__} took {elapsed:.2f}s (slow)")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {e}")
            raise
    
    return wrapper


class PerformanceTracker:
    """Track performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, operation: str, duration: float):
        """
        Record an operation duration
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        stats = self.metrics[operation]
        stats['count'] += 1
        stats['total_time'] += duration
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
    
    def get_stats(self, operation: Optional[str] = None) -> Dict:
        """
        Get performance statistics
        
        Args:
            operation: Specific operation (all if None)
        
        Returns:
            Dictionary with statistics
        """
        if operation:
            if operation in self.metrics:
                stats = self.metrics[operation].copy()
                stats['avg_time'] = stats['total_time'] / stats['count']
                return {operation: stats}
            return {}
        
        # All operations
        result = {}
        for op, stats in self.metrics.items():
            op_stats = stats.copy()
            op_stats['avg_time'] = stats['total_time'] / stats['count']
            result[op] = op_stats
        
        return result


# Global performance tracker
perf_tracker = PerformanceTracker()
