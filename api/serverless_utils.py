"""
Serverless optimization utilities for Vercel deployment
"""

import os
import sys
import time
import functools
from typing import Any, Callable, Dict, Optional
from contextlib import asynccontextmanager
from pathlib import Path

# Environment detection
IS_VERCEL = os.getenv("VERCEL", "0") == "1"
IS_SERVERLESS = IS_VERCEL or os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

class ServerlessOptimizer:
    """Optimizations for serverless environments"""
    
    @staticmethod
    def lazy_import(module_name: str, globals_dict: Dict[str, Any]) -> Callable:
        """Lazy import decorator to reduce cold start time"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if module_name not in globals_dict:
                    try:
                        module = __import__(module_name)
                        globals_dict[module_name] = module
                    except ImportError:
                        globals_dict[module_name] = None
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def cache_result(ttl_seconds: int = 60):
        """Simple result caching for serverless functions"""
        def decorator(func: Callable) -> Callable:
            cache = {}
            
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = str(args) + str(sorted(kwargs.items()))
                now = time.time()
                
                if key in cache:
                    result, timestamp = cache[key]
                    if now - timestamp < ttl_seconds:
                        return result
                
                result = await func(*args, **kwargs)
                cache[key] = (result, now)
                
                # Clean old entries
                if len(cache) > 100:  # Simple size limit
                    old_keys = [k for k, (_, ts) in cache.items() if now - ts > ttl_seconds]
                    for k in old_keys:
                        cache.pop(k, None)
                
                return result
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = str(args) + str(sorted(kwargs.items()))
                now = time.time()
                
                if key in cache:
                    result, timestamp = cache[key]
                    if now - timestamp < ttl_seconds:
                        return result
                
                result = func(*args, **kwargs)
                cache[key] = (result, now)
                
                # Clean old entries
                if len(cache) > 100:
                    old_keys = [k for k, (_, ts) in cache.items() if now - ts > ttl_seconds]
                    for k in old_keys:
                        cache.pop(k, None)
                
                return result
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @staticmethod
    def optimize_imports():
        """Optimize Python imports for faster cold starts"""
        if IS_SERVERLESS:
            # Pre-import commonly used modules
            import json
            import asyncio
            import datetime
            return True
        return False

# Serverless-optimized storage
class ServerlessStorage:
    """Memory storage optimized for serverless environments"""
    
    def __init__(self):
        self._data = {}
        self._stats = {
            "total_processed": 0,
            "total_errors": 0,
            "avg_urgency_score": 0.0,
            "last_processed": None,
            "processing_times": []
        }
        self._last_cleanup = time.time()
    
    def store(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store data with optional TTL"""
        entry = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl
        }
        self._data[key] = entry
        self._maybe_cleanup()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get data with TTL check"""
        if key not in self._data:
            return default
        
        entry = self._data[key]
        now = time.time()
        
        # Check TTL
        if entry.get("ttl") and (now - entry["timestamp"]) > entry["ttl"]:
            del self._data[key]
            return default
        
        return entry["value"]
    
    def _maybe_cleanup(self):
        """Periodic cleanup of expired entries"""
        now = time.time()
        if now - self._last_cleanup > 300:  # Every 5 minutes
            expired_keys = []
            for key, entry in self._data.items():
                if entry.get("ttl") and (now - entry["timestamp"]) > entry["ttl"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._data[key]
            
            self._last_cleanup = now
    
    def update_stats(self, **kwargs):
        """Update processing statistics"""
        self._stats.update(kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self._stats.copy()

# Global serverless storage instance
serverless_storage = ServerlessStorage() if IS_SERVERLESS else None

# Environment-specific configuration
def get_serverless_config() -> Dict[str, Any]:
    """Get configuration optimized for serverless environment"""
    config = {
        "max_memory_mb": 128,  # Vercel default
        "max_execution_time": 30,  # Vercel default
        "enable_caching": True,
        "cache_ttl": 300,  # 5 minutes
        "cleanup_interval": 300,  # 5 minutes
    }
    
    if IS_VERCEL:
        config.update({
            "log_format": "json",
            "enable_console_colors": False,
            "async_processing": True,
        })
    
    return config

# Startup optimization
def optimize_for_serverless():
    """Apply serverless optimizations"""
    if not IS_SERVERLESS:
        return False
    
    # Optimize Python path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Pre-import critical modules
    ServerlessOptimizer.optimize_imports()
    
    # Set memory limits if available
    try:
        import resource
        # Set memory limit to 80% of available (conservative)
        if IS_VERCEL:
            memory_limit = 100 * 1024 * 1024  # 100MB for Vercel
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
    except (ImportError, OSError):
        pass  # Not available on all systems
    
    return True

# Initialize optimizations
if IS_SERVERLESS:
    optimize_for_serverless()
