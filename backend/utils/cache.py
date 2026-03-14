"""
Bounded cache utilities to prevent memory leaks.

Provides LRU (Least Recently Used) caches with maximum size limits
to prevent unbounded memory growth in high-load scenarios.
"""

import threading
from collections import OrderedDict
from typing import Any, Dict, Generic, Optional, TypeVar

KT = TypeVar('KT')  # Key type
VT = TypeVar('VT')  # Value type


class LRUCache(Generic[KT, VT]):
    """
    Thread-safe LRU cache with maximum size limit.
    
    When the cache reaches max_size, the least recently used item is evicted.
    All operations are O(1) thanks to OrderedDict.
    
    Features:
    - Thread-safe with internal lock
    - Automatic eviction of oldest items
    - Configurable maximum size
    - O(1) get/set/delete operations
    
    Example:
        cache = LRUCache[str, dict](max_size=1000)
        cache.set("key1", {"data": "value"})
        value = cache.get("key1")
        cache.delete("key1")
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of items to store (default: 1000)
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        
        self._cache: OrderedDict[KT, VT] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: KT, default: Optional[VT] = None) -> Optional[VT]:
        """
        Get value by key, moving it to end (most recently used).
        
        Args:
            key: Key to lookup
            default: Default value if key not found
            
        Returns:
            Value if found, default otherwise
        """
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            else:
                self._misses += 1
                return default
    
    def set(self, key: KT, value: VT) -> None:
        """
        Set key-value pair, evicting oldest item if cache is full.
        
        Args:
            key: Key to set
            value: Value to store
        """
        with self._lock:
            if key in self._cache:
                # Update existing key and move to end
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                # Add new key
                self._cache[key] = value
                # Evict oldest if over limit
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)  # Remove oldest (first) item
    
    def delete(self, key: KT) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Key to delete
            
        Returns:
            True if key was found and deleted, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Remove all items from cache."""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Return current number of items in cache."""
        with self._lock:
            return len(self._cache)
    
    def max_size(self) -> int:
        """Return maximum cache size."""
        return self._max_size
    
    def stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.
        
        Returns:
            Dictionary with hits, misses, size, and hit rate
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hit_rate": f"{hit_rate:.2f}%",
            }
    
    def keys(self) -> list:
        """Return list of all keys (from oldest to newest)."""
        with self._lock:
            return list(self._cache.keys())
    
    def values(self) -> list:
        """Return list of all values (from oldest to newest)."""
        with self._lock:
            return list(self._cache.values())
    
    def items(self) -> list:
        """Return list of (key, value) tuples (from oldest to newest)."""
        with self._lock:
            return list(self._cache.items())
    
    def __contains__(self, key: KT) -> bool:
        """Check if key exists in cache (doesn't update LRU order)."""
        with self._lock:
            return key in self._cache
    
    def __len__(self) -> int:
        """Return number of items in cache."""
        with self._lock:
            return len(self._cache)
    
    def __repr__(self) -> str:
        """String representation of cache."""
        return f"LRUCache(size={self.size()}, max_size={self._max_size})"
