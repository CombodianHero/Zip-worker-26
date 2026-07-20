"""
Logging utility for the bot.
Provides consistent, colored logging across all modules.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from config import config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI colors for console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        record.name = f"\033[34m{record.name}\033[0m"  # Blue module name
        return super().format(record)


class Logger:
    """Singleton logger manager for the application."""
    
    _instance: Optional["Logger"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if not self._initialized:
            self._setup()
            self._initialized = True
    
    def _setup(self) -> None:
        """Configure logging handlers and formatters."""
        self.root = logging.getLogger("saini_txt")
        self.root.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        self.root.propagate = False
        
        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(ColoredFormatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        self.root.addHandler(console)
        
        # File handler
        log_file = config.BASE_DIR / config.LOG_FILE
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | "
            "%(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        self.root.addHandler(file_handler)
    
    def get(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific module.
        
        Args:
            name: Module name (e.g., 'downloader.pw')
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(f"saini_txt.{name}")


# Global logger factory
_logger = Logger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module name.
    
    Args:
        name: Module name
        
    Returns:
        Logger instance
    """
    return _logger.get(name)
