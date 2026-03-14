"""
Retry utilities for handling transient failures.

Provides decorators and functions for retrying failed operations
with exponential backoff and configurable retry logic.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union
import logging

T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


def is_transient_error(exception: Exception) -> bool:
    """
    Check if an exception is transient and worth retrying.
    
    Transient errors include:
    - Network timeouts
    - Connection errors
    - Temporary service unavailability
    - Rate limiting
    
    Args:
        exception: The exception to check
        
    Returns:
        True if error is transient, False otherwise
    """
    error_msg = str(exception).lower()
    
    # Network/connection errors
    transient_patterns = [
        "timeout",
        "connection",
        "network",
        "unreachable",
        "refused",
        "reset",
        "broken pipe",
        "service unavailable",
        "too many requests",
        "rate limit",
        "503",
        "504",
        "502",
    ]
    
    return any(pattern in error_msg for pattern in transient_patterns)


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        retry_on: Tuple of exception types to retry on (default: all transient)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: If all retry attempts are exhausted
        
    Example:
        result = await retry_async(
            some_async_function,
            arg1, arg2,
            max_attempts=5,
            retry_on=(asyncio.TimeoutError, ConnectionError)
        )
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Retry succeeded on attempt {attempt}")
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry this exception
            should_retry = False
            if retry_on:
                should_retry = isinstance(e, retry_on)
            else:
                should_retry = is_transient_error(e)
            
            if not should_retry or attempt >= max_attempts:
                if attempt >= max_attempts:
                    logger.error(f"All {max_attempts} retry attempts exhausted")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise RetryError(f"Failed after {max_attempts} attempts") from last_exception
    raise RetryError(f"Failed after {max_attempts} attempts")


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any,
) -> T:
    """
    Retry a synchronous function with exponential backoff.
    
    Args:
        func: Synchronous function to retry
        *args: Positional arguments for the function
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        retry_on: Tuple of exception types to retry on (default: all transient)
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: If all retry attempts are exhausted
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Retry succeeded on attempt {attempt}")
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry this exception
            should_retry = False
            if retry_on:
                should_retry = isinstance(e, retry_on)
            else:
                should_retry = is_transient_error(e)
            
            if not should_retry or attempt >= max_attempts:
                if attempt >= max_attempts:
                    logger.error(f"All {max_attempts} retry attempts exhausted")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            time.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise RetryError(f"Failed after {max_attempts} attempts") from last_exception
    raise RetryError(f"Failed after {max_attempts} attempts")


def with_retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retry_on: Tuple of exception types to retry on
        
    Example:
        @with_retry_async(max_attempts=5)
        async def fetch_data():
            # ... code that might fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retry_on=retry_on,
                **kwargs,
            )
        return wrapper
    return decorator


def with_retry_sync(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator for adding retry logic to synchronous functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retry_on: Tuple of exception types to retry on
        
    Example:
        @with_retry_sync(max_attempts=5)
        def fetch_data():
            # ... code that might fail transiently
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_sync(
                func,
                *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retry_on=retry_on,
                **kwargs,
            )
        return wrapper
    return decorator
