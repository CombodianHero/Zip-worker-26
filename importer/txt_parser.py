"""
TXT file parser for course content.
Handles various URL formats including PW, YouTube, and direct links.
"""

from pathlib import Path
from typing import List, Tuple, Optional
import re

from utils.logger import get_logger


class TxtParser:
    """
    Parses TXT files containing course content links.
    
    Format: Lecture Title:URL
    
    Handles:
    - Standard URLs
    - PW video URLs (childId/parentId format)
    - YouTube URLs
    - PDF URLs
    - Any valid HTTP/HTTPS URL
    """
    
    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        
        # URL patterns - tries each in order
        self.patterns = [
            # Title:URL format
            re.compile(r"^(.+?):(https?://.+)$", re.IGNORECASE),
            # Direct URL (no title)
            re.compile(r"^(https?://.+)$", re.IGNORECASE),
        ]
    
    def parse_file(self, file_path: Path) -> List[Tuple[str, str]]:
        """
        Parse a TXT file and extract (title, url) pairs.
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            List of (title, url) tuples
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        items: List[Tuple[str, str]] = []
        
        # Try multiple encodings
        content = self._read_file(file_path)
        if content is None:
            return items
        
        lines = content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip comments
            if line.startswith("#") or line.startswith("//"):
                continue
            
            # Parse line
            result = self.parse_line(line)
            if result:
                items.append(result)
            else:
                self.logger.warning(
                    f"Line {line_num}: Invalid format - {line[:100]}"
                )
        
        self.logger.info(
            f"Parsed {len(items)} items from {file_path.name}"
        )
        return items
    
    def parse_line(self, line: str) -> Optional[Tuple[str, str]]:
        """
        Parse a single line into (title, url).
        
        Args:
            line: Line to parse
            
        Returns:
            (title, url) tuple or None if invalid
        """
        for pattern in self.patterns:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                
                if len(groups) == 2:
                    title, url = groups
                else:
                    url = groups[0]
                    title = self._generate_title(url)
                
                title = title.strip()
                url = url.strip()
                
                if self._is_valid_url(url):
                    return (title, url)
        
        return None
    
    def _read_file(self, file_path: Path) -> Optional[str]:
        """
        Read file with multiple encoding attempts.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content or None
        """
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.logger.error(f"Error reading file: {e}")
                return None
        
        self.logger.error(f"Could not read file with any encoding: {file_path}")
        return None
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid URL
        """
        if not url.startswith(("http://", "https://")):
            return False
        
        # Basic URL structure validation
        pattern = re.compile(
            r"^https?://"
            r"[\w\-]+(\.[\w\-]+)+"
            r"[/\w\-\.?=&%#+]*$",
            re.IGNORECASE,
        )
        
        return bool(pattern.match(url))
    
    def _generate_title(self, url: str) -> str:
        """
        Generate a title from URL if none provided.
        
        Args:
            url: Download URL
            
        Returns:
            Generated title
        """
        # Check for PW video
        if "childId" in url and "parentId" in url:
            return "PW Video Lecture"
        
        # Check for YouTube
        if "youtube.com" in url or "youtu.be" in url:
            return "YouTube Video"
        
        # Try to extract filename from URL path
        try:
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            path = parsed.path
            
            if path and "/" in path:
                filename = path.split("/")[-1]
                if filename:
                    # Remove extension
                    name = filename.rsplit(".", 1)[0]
                    # Clean up
                    name = name.replace("-", " ").replace("_", " ")
                    name = unquote(name)
                    if name:
                        return name
        except Exception:
            pass
        
        return "Course Resource"
