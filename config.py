"""
Configuration module for Saini Txt 2026 Bot.
Centralizes all settings from environment variables.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Main configuration for the bot."""
    
    # ==================== Telegram API ====================
    API_ID: int = field(
        default_factory=lambda: int(os.getenv("API_ID", "0"))
    )
    API_HASH: str = field(
        default_factory=lambda: os.getenv("API_HASH", "")
    )
    BOT_TOKEN: str = field(
        default_factory=lambda: os.getenv("BOT_TOKEN", "")
    )
    BOT_USERNAME: str = field(
        default_factory=lambda: os.getenv("BOT_USERNAME", "")
    )
    
    # ==================== User Management ====================
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(uid.strip()) 
        for uid in os.getenv("ADMIN_IDS", "").split(",") 
        if uid.strip()
    ])
    ALLOWED_USERS: List[int] = field(default_factory=lambda: [
        int(uid.strip()) 
        for uid in os.getenv("ALLOWED_USERS", "").split(",") 
        if uid.strip()
    ])
    
    # ==================== Physics Wallah ====================
    PW_TOKEN: str = field(
        default_factory=lambda: os.getenv("PW_TOKEN", "")
    )
    PW_API_URL: str = field(
        default_factory=lambda: os.getenv(
            "PW_API_URL",
            "https://anonymouspwplayeer-2038df9c1dbd.herokuapp.com"
        )
    )
    PW_HEADERS: dict = field(default_factory=lambda: {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.pw.live",
        "Referer": "https://www.pw.live/",
        "Connection": "keep-alive",
    })
    
    # ==================== Paths ====================
    BASE_DIR: Path = field(
        default_factory=lambda: Path(__file__).parent
    )
    DOWNLOADS_DIR: Path = field(
        default_factory=lambda: Path("downloads")
    )
    TEMP_DIR: Path = field(
        default_factory=lambda: Path("temp")
    )
    LOGS_DIR: Path = field(
        default_factory=lambda: Path("logs")
    )
    DATABASE_DIR: Path = field(
        default_factory=lambda: Path("database")
    )
    THUMBNAILS_DIR: Path = field(
        default_factory=lambda: Path("thumbnails")
    )
    
    # ==================== Database ====================
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite:///database/courses.db"
        )
    )
    
    # ==================== Download Settings ====================
    MAX_CONCURRENT_DOWNLOADS: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "1"))
    )
    DOWNLOAD_CHUNK_SIZE: int = field(
        default_factory=lambda: int(os.getenv("DOWNLOAD_CHUNK_SIZE", "1048576"))
    )
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    DOWNLOAD_TIMEOUT: int = 600
    
    # ==================== Upload Settings ====================
    UPLOAD_CHUNK_SIZE: int = 2 * 1024 * 1024
    MAX_FILE_SIZE: int = 2 * 1024 * 1024 * 1024
    THUMBNAIL_SIZE: tuple = (320, 320)
    VIDEO_THUMBNAIL_TIME: int = 5
    
    # ==================== Logging ====================
    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    LOG_FILE: str = field(
        default_factory=lambda: os.getenv("LOG_FILE", "logs/bot.log")
    )
    
    # ==================== Feature Flags ====================
    ENABLE_THUMBNAILS: bool = True
    ENABLE_PROGRESS_BAR: bool = True
    ENABLE_CAPTIONS: bool = True
    AUTO_CLEAN_TEMP: bool = True
    DUPLICATE_CHECK: bool = True
    
    def __post_init__(self) -> None:
        """Create required directories."""
        for dir_path in [
            self.DOWNLOADS_DIR,
            self.TEMP_DIR,
            self.LOGS_DIR,
            self.DATABASE_DIR,
            self.THUMBNAILS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """
        Validate required configuration.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If required config is missing
        """
        required = {
            "API_ID": self.API_ID,
            "API_HASH": self.API_HASH,
            "BOT_TOKEN": self.BOT_TOKEN,
        }
        
        missing = [k for k, v in required.items() if not v]
        
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}\n"
                f"Please check your .env file."
            )
        
        if not self.PW_TOKEN:
            print("⚠️ Warning: PW_TOKEN not set. PW video downloads may not work.")
        
        return True


# Global configuration instance
config = Config()
