"""
Redis operation utilities with retry logic and error handling.

Provides safe Redis operations that handle transient failures gracefully.
"""

from typing import Any, Optional
from config import redis_client
import logging

logger = logging.getLogger(__name__)


def redis_get(key: str, default: Any = None, max_attempts: int = 2) -> Any:
    """
    Safe Redis GET with retry logic.
    
    Args:
        key: Redis key
        default: Default value if key not found or error occurs
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        Value from Redis or default
    """
    if not redis_client:
        return default
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = redis_client.get(key)
            return result if result is not None else default
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis GET failed after {max_attempts} attempts: {e}")
                return default
            logger.debug(f"Redis GET attempt {attempt} failed: {e}")
    
    return default


def redis_set(key: str, value: Any, ex: Optional[int] = None, max_attempts: int = 2) -> bool:
    """
    Safe Redis SET with retry logic.
    
    Args:
        key: Redis key
        value: Value to set
        ex: Expiration time in seconds
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    for attempt in range(1, max_attempts + 1):
        try:
            if ex:
                redis_client.setex(key, ex, value)
            else:
                redis_client.set(key, value)
            return True
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis SET failed after {max_attempts} attempts: {e}")
                return False
            logger.debug(f"Redis SET attempt {attempt} failed: {e}")
    
    return False


def redis_delete(key: str, *keys: str, max_attempts: int = 2) -> int:
    """
    Safe Redis DELETE with retry logic.
    
    Args:
        key: First Redis key to delete
        *keys: Additional keys to delete
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        Number of keys deleted, or 0 on error
    """
    if not redis_client:
        return 0
    
    all_keys = (key,) + keys
    
    for attempt in range(1, max_attempts + 1):
        try:
            return redis_client.delete(*all_keys)
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis DELETE failed after {max_attempts} attempts: {e}")
                return 0
            logger.debug(f"Redis DELETE attempt {attempt} failed: {e}")
    
    return 0


def redis_incr(key: str, amount: int = 1, max_attempts: int = 2) -> Optional[int]:
    """
    Safe Redis INCR with retry logic.
    
    Args:
        key: Redis key
        amount: Amount to increment by (default: 1)
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        New value after increment, or None on error
    """
    if not redis_client:
        return None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if amount == 1:
                return redis_client.incr(key)
            else:
                return redis_client.incrby(key, amount)
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis INCR failed after {max_attempts} attempts: {e}")
                return None
            logger.debug(f"Redis INCR attempt {attempt} failed: {e}")
    
    return None


def redis_expire(key: str, seconds: int, max_attempts: int = 2) -> bool:
    """
    Safe Redis EXPIRE with retry logic.
    
    Args:
        key: Redis key
        seconds: Expiration time in seconds
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        True if successful, False otherwise
    """
    if not redis_client:
        return False
    
    for attempt in range(1, max_attempts + 1):
        try:
            return bool(redis_client.expire(key, seconds))
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis EXPIRE failed after {max_attempts} attempts: {e}")
                return False
            logger.debug(f"Redis EXPIRE attempt {attempt} failed: {e}")
    
    return False


def redis_pipeline_execute(pipeline_ops: list, max_attempts: int = 2) -> Optional[list]:
    """
    Safe Redis pipeline execution with retry logic.
    
    Args:
        pipeline_ops: List of (method, args, kwargs) tuples for pipeline operations
        max_attempts: Maximum retry attempts (default: 2)
        
    Returns:
        List of results or None on error
        
    Example:
        ops = [
            ('incr', ('key1',), {}),
            ('expire', ('key1', 60), {}),
        ]
        results = redis_pipeline_execute(ops)
    """
    if not redis_client:
        return None
    
    for attempt in range(1, max_attempts + 1):
        try:
            pipe = redis_client.pipeline()
            for method, args, kwargs in pipeline_ops:
                getattr(pipe, method)(*args, **kwargs)
            return pipe.execute()
        except Exception as e:
            if attempt >= max_attempts:
                logger.warning(f"Redis pipeline failed after {max_attempts} attempts: {e}")
                return None
            logger.debug(f"Redis pipeline attempt {attempt} failed: {e}")
    
    return None
