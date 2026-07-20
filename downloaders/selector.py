"""
Intelligent downloader selector for routing URLs to appropriate downloaders.
"""

from pathlib import Path
from typing import List, Tuple, Optional, Callable
import asyncio

from models.course_item import CourseItem
from downloaders.base import BaseDownloader
from downloaders.pw_downloader import PWDownloader
from downloaders.pdf_downloader import PdfDownloader
from downloaders.mp4_downloader import Mp4Downloader
from downloaders.youtube_downloader import YouTubeDownloader
from downloaders.drm_downloader import DrmDownloader
from downloaders.generic_downloader import GenericDownloader
from config import config
from utils.logger import get_logger


class DownloaderSelector:
    """
    Routes download requests to the most appropriate downloader.
    
    Priority order:
    1. PW Downloader (Physics Wallah videos)
    2. PDF Downloader
    3. YouTube Downloader
    4. DRM Downloader (streaming content)
    5. MP4 Downloader (direct videos)
    6. Generic Downloader (fallback)
    """
    
    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        
        # Initialize downloaders in priority order
        self.downloaders: List[BaseDownloader] = [
            PWDownloader(),
            PdfDownloader(),
            YouTubeDownloader(),
            DrmDownloader(),
            Mp4Downloader(),
            GenericDownloader(),
        ]
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
        
        # Statistics
        self._stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "by_downloader": {},
        }
    
    async def download(
        self,
        item: CourseItem,
        output_dir: Path,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[Path, str]:
        """
        Download using the best available downloader.
        
        Args:
            item: CourseItem to download
            output_dir: Output directory
            progress_callback: Progress callback
            
        Returns:
            Tuple of (file_path, extension)
        """
        async with self._semaphore:
            self._stats["total"] += 1
            
            # Try each downloader in priority order
            errors = []
            
            for downloader in self.downloaders:
                try:
                    if await downloader.can_handle(item.url):
                        name = downloader.__class__.__name__
                        self.logger.info(f"Using {name} for: {item.title[:50]}")
                        
                        file_path, extension = await downloader.download(
                            item,
                            output_dir,
                            progress_callback,
                        )
                        
                        # Success
                        self._stats["successful"] += 1
                        self._stats["by_downloader"][name] = (
                            self._stats["by_downloader"].get(name, 0) + 1
                        )
                        
                        item.mark_downloaded(file_path, extension, name)
                        
                        return file_path, extension
                        
                except Exception as e:
                    name = downloader.__class__.__name__
                    errors.append(f"{name}: {str(e)[:100]}")
                    self.logger.warning(f"{name} failed: {e}")
                    continue
            
            # All downloaders failed
            self._stats["failed"] += 1
            raise Exception(f"All downloaders failed: {'; '.join(errors[-3:])}")
    
    def get_stats(self) -> dict:
        """Get download statistics."""
        return self._stats.copy()
    
    async def cleanup(self) -> None:
        """Cleanup all downloaders."""
        for downloader in self.downloaders:
            await downloader._close_session()
