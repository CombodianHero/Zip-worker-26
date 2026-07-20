"""
Helper utility functions used across the application.
"""

import re
import hashlib
import asyncio
from pathlib import Path
from typing import List, Any, Callable, TypeVar
from urllib.parse import urlparse

T = TypeVar("T")


def format_size(size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 GB')
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_time(seconds: float) -> str:
    """
    Format time duration in human-readable format.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted string (e.g., '2m 30s')
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_speed(bytes_per_sec: float) -> str:
    """
    Format download speed in human-readable format.
    
    Args:
        bytes_per_sec: Speed in bytes per second
        
    Returns:
        Formatted string (e.g., '5.2 MB/s')
    """
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        filename: String to sanitize
        max_length: Maximum length
        
    Returns:
        Safe filename string
    """
    # Remove unsafe characters
    safe = "".join(
        c for c in filename 
        if c.isalnum() or c in " -_."
    ).strip()
    
    # Replace spaces
    safe = safe.replace(" ", "_")
    
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    
    # Truncate
    if len(safe) > max_length:
        safe = safe[:max_length]
    
    return safe if safe else "unnamed"


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
        
    Returns:
        Domain string (e.g., 'example.com')
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return "unknown"


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL
    """
    if not url.startswith(("http://", "https://")):
        return False
    
    pattern = re.compile(
        r"^https?://"
        r"[\w\-]+(\.[\w\-]+)+"
        r"[/\w\-\.?=&%#+]*$",
        re.IGNORECASE,
    )
    
    return bool(pattern.match(url))


def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunked lists
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments
        max_retries: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        **kwargs: Keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff ** attempt)
                await asyncio.sleep(wait_time)
    
    raise last_exception


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)
        
    Returns:
        Hex digest string
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()
