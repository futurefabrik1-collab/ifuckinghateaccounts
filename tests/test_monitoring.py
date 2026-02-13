"""
Tests for monitoring.py module
"""

import pytest
from src.utils.monitoring import (
    PerformanceTracker, 
    get_uptime, 
    get_disk_usage, 
    get_memory_usage,
    get_health_status,
    monitor_performance
)


class TestPerformanceTracker:
    """Test performance tracker functionality"""
    
    @pytest.fixture
    def tracker(self):
        """Create performance tracker"""
        return PerformanceTracker()
    
    def test_record_operation(self, tracker):
        """Test recording an operation"""
        tracker.record('ocr', 2.5)
        
        stats = tracker.get_stats('ocr')
        
        assert 'ocr' in stats
        assert stats['ocr']['count'] == 1
        assert stats['ocr']['total_time'] == 2.5
        assert stats['ocr']['min_time'] == 2.5
        assert stats['ocr']['max_time'] == 2.5
    
    def test_record_multiple_operations(self, tracker):
        """Test recording multiple operations"""
        tracker.record('ocr', 1.0)
        tracker.record('ocr', 2.0)
        tracker.record('ocr', 3.0)
        
        stats = tracker.get_stats('ocr')
        
        assert stats['ocr']['count'] == 3
        assert stats['ocr']['total_time'] == 6.0
        assert stats['ocr']['min_time'] == 1.0
        assert stats['ocr']['max_time'] == 3.0
        assert stats['ocr']['avg_time'] == 2.0
    
    def test_get_stats_single_operation(self, tracker):
        """Test getting stats for specific operation"""
        tracker.record('match', 1.5)
        tracker.record('ocr', 2.5)
        
        stats = tracker.get_stats('match')
        
        assert 'match' in stats
        assert 'ocr' not in stats
    
    def test_get_stats_all_operations(self, tracker):
        """Test getting stats for all operations"""
        tracker.record('ocr', 1.0)
        tracker.record('match', 2.0)
        tracker.record('scan', 3.0)
        
        stats = tracker.get_stats()
        
        assert 'ocr' in stats
        assert 'match' in stats
        assert 'scan' in stats
    
    def test_get_stats_nonexistent_operation(self, tracker):
        """Test getting stats for operation that doesn't exist"""
        stats = tracker.get_stats('nonexistent')
        
        assert stats == {}
    
    def test_average_calculation(self, tracker):
        """Test average time calculation"""
        tracker.record('test', 1.0)
        tracker.record('test', 3.0)
        tracker.record('test', 2.0)
        
        stats = tracker.get_stats('test')
        
        assert stats['test']['avg_time'] == 2.0
    
    def test_min_max_tracking(self, tracker):
        """Test min/max time tracking"""
        tracker.record('test', 5.0)
        tracker.record('test', 1.0)
        tracker.record('test', 10.0)
        tracker.record('test', 3.0)
        
        stats = tracker.get_stats('test')
        
        assert stats['test']['min_time'] == 1.0
        assert stats['test']['max_time'] == 10.0


class TestMonitoringFunctions:
    """Test monitoring utility functions"""
    
    def test_get_uptime(self):
        """Test uptime calculation"""
        uptime = get_uptime()
        
        assert 'seconds' in uptime
        assert 'formatted' in uptime
        assert 'started_at' in uptime
        assert uptime['seconds'] >= 0
    
    def test_get_disk_usage(self, tmp_path):
        """Test disk usage check"""
        usage = get_disk_usage(tmp_path)
        
        assert 'total_gb' in usage
        assert 'used_gb' in usage
        assert 'free_gb' in usage
        assert 'percent_used' in usage
        assert usage['total_gb'] > 0
    
    def test_get_memory_usage(self):
        """Test memory usage check"""
        memory = get_memory_usage()
        
        assert 'total_mb' in memory
        assert 'used_mb' in memory
        assert 'available_mb' in memory
        assert 'percent_used' in memory
        assert memory['total_mb'] > 0
    
    def test_get_health_status(self):
        """Test overall health status"""
        health = get_health_status()
        
        assert 'status' in health
        assert 'timestamp' in health
        assert 'checks' in health
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
    
    def test_monitor_performance_decorator(self):
        """Test performance monitoring decorator"""
        
        @monitor_performance
        def test_function():
            import time
            time.sleep(0.1)
            return "success"
        
        result = test_function()
        
        assert result == "success"
    
    def test_monitor_performance_with_exception(self):
        """Test performance monitoring with exceptions"""
        
        @monitor_performance
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_function()
