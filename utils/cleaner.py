"""
Temporary file cleaner utility.
Automatically cleans up old temporary files.
"""

import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from config import config
from utils.logger import get_logger


class TempFileCleaner:
    """
    Automatic cleaner for temporary files and directories.
    
    Features:
    - Age-based cleaning
    - Size-based cleaning
    - Scheduled cleaning
    - Manual cleaning
    """
    
    def __init__(
        self,
        temp_dir: Optional[Path] = None,
        max_age_hours: int = 24,
        max_size_gb: float = 10.0,
        check_interval: int = 3600,
    ) -> None:
        """
        Initialize cleaner.
        
        Args:
            temp_dir: Directory to clean
            max_age_hours: Maximum file age in hours
            max_size_gb: Maximum directory size in GB
            check_interval: Clean check interval in seconds
        """
        self.logger = get_logger(__name__)
        self.temp_dir = temp_dir or config.TEMP_DIR
        self.max_age = timedelta(hours=max_age_hours)
        self.max_size = max_size_gb * 1024 * 1024 * 1024  # Convert to bytes
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start automatic cleaning."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._clean_loop())
        self.logger.info("Temp file cleaner started")
    
    async def stop(self) -> None:
        """Stop automatic cleaning."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("Temp file cleaner stopped")
    
    async def _clean_loop(self) -> None:
        """Main cleaning loop."""
        while self._running:
            try:
                await self.clean()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Clean error: {e}")
                await asyncio.sleep(60)
    
    async def clean(self) -> dict:
        """
        Perform cleaning of temporary files.
        
        Returns:
            Dictionary with cleaning statistics
        """
        if not self.temp_dir.exists():
            return {"cleaned": 0, "freed_bytes": 0}
        
        stats = {"cleaned": 0, "freed_bytes": 0}
        now = datetime.now()
        
        # Clean old files
        for file_path in self.temp_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            try:
                # Check age
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                age = now - mtime
                
                if age > self.max_age:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    stats["cleaned"] += 1
                    stats["freed_bytes"] += size
                    self.logger.debug(f"Cleaned old file: {file_path.name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to clean {file_path}: {e}")
        
        # Clean empty directories
        for dir_path in sorted(
            self.temp_dir.rglob("*"),
            key=lambda p: len(str(p)),
            reverse=True,
        ):
            if dir_path.is_dir() and dir_path != self.temp_dir:
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except Exception:
                    pass
        
        # Check total size
        total_size = self._get_dir_size(self.temp_dir)
        if total_size > self.max_size:
            self.logger.warning(
                f"Temp directory exceeds max size: "
                f"{self._format_size(total_size)} > {self._format_size(self.max_size)}"
            )
            # Force clean all files
            await self.force_clean()
        
        if stats["cleaned"] > 0:
            self.logger.info(
                f"Cleaned {stats['cleaned']} files, "
                f"freed {self._format_size(stats['freed_bytes'])}"
            )
        
        return stats
    
    async def force_clean(self) -> None:
        """Force clean all files in temp directory."""
        if not self.temp_dir.exists():
            return
        
        for item in self.temp_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                self.logger.warning(f"Force clean failed for {item}: {e}")
        
        self.logger.info("Force clean completed")
    
    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """Calculate total size of a directory."""
        return sum(
            f.stat().st_size 
            for f in path.rglob("*") 
            if f.is_file()
        )
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
