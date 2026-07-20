"""
Physics Wallah (PW) Video Downloader
Handles PW's encrypted video streaming with token-based authentication.
"""

from pathlib import Path
from typing import Optional, Tuple, Callable
import asyncio
import json
import re
import subprocess

from models.course_item import CourseItem
from downloaders.base import BaseDownloader
from config import config
from utils.logger import get_logger


class PWDownloader(BaseDownloader):
    """
    Downloads Physics Wallah videos using the proxy API.
    
    URL Format:
    Original: https://www.pw.live/study/...?childId=xxx&parentId=xxx
    Converted: https://anonymouspwplayeer-2038df9c1dbd.herokuapp.com/pw?url={url}&token={token}
    
    The proxy API handles:
    - Authentication
    - DRM decryption
    - Stream extraction
    - Quality selection
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(__name__)
        self.timeout = 900  # 15 minutes for PW videos
        
        # PW specific settings from config
        self.pw_token = config.PW_TOKEN
        self.pw_api_url = config.PW_API_URL.rstrip("/")
        self.pw_headers = config.PW_HEADERS.copy()
    
    async def can_handle(self, url: str) -> bool:
        """
        Check if URL is a Physics Wallah video.
        
        Detects PW URLs by checking for:
        - childId and parentId parameters
        - pw.live domain
        
        Args:
            url: Download URL
            
        Returns:
            True if this is a PW video URL
        """
        # Primary check: childId and parentId parameters
        if "childId" in url and "parentId" in url:
            return True
        
        # Secondary check: PW domain
        if "pw.live" in url.lower():
            return True
        
        # Check for PW study URLs
        if "pw.live/study" in url.lower():
            return True
        
        return False
    
    async def download(
        self,
        item: CourseItem,
        output_dir: Path,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[Path, str]:
        """
        Download a PW video.
        
        Process:
        1. Build proxy API URL with token
        2. Request video stream URL from proxy
        3. Download the stream using ffmpeg or direct download
        
        Args:
            item: CourseItem with PW URL
            output_dir: Output directory for downloaded file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (file_path, file_extension)
            
        Raises:
            ValueError: If PW_TOKEN is not configured
            Exception: If download fails
        """
        self.logger.info(f"📥 Downloading PW video: {item.title[:50]}")
        
        # Validate token
        if not self.pw_token:
            raise ValueError(
                "PW_TOKEN is not configured. "
                "Set PW_TOKEN in your .env file to download PW videos."
            )
        
        # Generate output path
        output_path = self._get_safe_path(item, "mp4", output_dir)
        
        try:
            # Step 1: Get stream URL from proxy API
            stream_url = await self._get_stream_url(item.url)
            
            if not stream_url:
                raise Exception("Failed to get PW video stream URL from API")
            
            self.logger.info(f"✅ Got stream URL for: {item.title[:50]}")
            
            # Step 2: Download the stream
            success = await self._download_stream(
                stream_url,
                output_path,
                progress_callback,
                item,
            )
            
            if not success:
                raise Exception("Failed to download PW video stream")
            
            # Step 3: Verify downloaded file
            if not output_path.exists():
                raise Exception("Downloaded file not found")
            
            file_size = output_path.stat().st_size
            if file_size == 0:
                raise Exception("Downloaded file is empty")
            
            self.logger.info(
                f"✅ PW video downloaded: {item.title[:50]} "
                f"({self._format_size(file_size)})"
            )
            
            return output_path, "mp4"
            
        except Exception as e:
            self.logger.error(f"❌ PW download failed: {e}")
            raise
    
    async def _get_stream_url(self, original_url: str) -> Optional[str]:
        """
        Get actual video stream URL from the PW proxy API.
        
        The API converts PW's encrypted video URL into a downloadable stream.
        
        API Endpoint: {PW_API_URL}/pw
        Parameters:
        - url: Original PW video URL
        - token: Authentication token
        
        Args:
            original_url: Original PW video URL with childId/parentId
            
        Returns:
            Direct stream URL (M3U8 or MP4) or None if failed
        """
        try:
            # Build API URL
            api_url = f"{self.pw_api_url}/pw"
            
            # Build query parameters
            params = {
                "url": original_url,
                "token": self.pw_token,
            }
            
            self.logger.info(f"🔗 Requesting PW API: {api_url}")
            self.logger.debug(f"URL: {original_url[:100]}")
            
            # Make API request
            session = await self._get_session()
            
            async with session.get(
                api_url,
                params=params,
                headers=self.pw_headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(
                        f"PW API error: HTTP {response.status}\n"
                        f"Response: {error_text[:300]}"
                    )
                    return None
                
                # Parse response
                content_type = response.headers.get("Content-Type", "")
                
                if "application/json" in content_type:
                    data = await response.json()
                else:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        # Maybe it's a direct URL
                        if text.startswith("http"):
                            return text.strip()
                        self.logger.error(f"Invalid JSON response: {text[:200]}")
                        return None
                
                # Extract stream URL from response
                stream_url = self._extract_url_from_response(data)
                
                if stream_url:
                    self.logger.info("✅ Successfully extracted stream URL")
                    return stream_url
                else:
                    self.logger.error(f"No stream URL found in response: {data}")
                    return None
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error calling PW API: {e}")
            return None
        except asyncio.TimeoutError:
            self.logger.error("PW API request timed out")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    def _extract_url_from_response(self, data) -> Optional[str]:
        """
        Extract stream URL from the API response.
        
        The API might return different formats:
        - Direct URL string
        - JSON object with 'url' field
        - JSON object with 'data.url' nested field
        - JSON object with 'stream_url' field
        
        Args:
            data: API response data (dict, list, or string)
            
        Returns:
            Stream URL or None
        """
        # If it's a string
        if isinstance(data, str):
            if data.startswith("http"):
                return data
            # Try parsing as JSON
            try:
                data = json.loads(data)
            except:
                return None
        
        # If it's a dict
        if isinstance(data, dict):
            # Common response fields
            url_keys = ["url", "stream_url", "video_url", "download_url", "link"]
            
            for key in url_keys:
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value
            
            # Check nested 'data' field
            if "data" in data:
                nested = data["data"]
                if isinstance(nested, str) and nested.startswith("http"):
                    return nested
                if isinstance(nested, dict):
                    for key in url_keys:
                        value = nested.get(key)
                        if isinstance(value, str) and value.startswith("http"):
                            return value
            
            # Check 'result' field
            if "result" in data:
                result = data["result"]
                if isinstance(result, str) and result.startswith("http"):
                    return result
                if isinstance(result, dict):
                    for key in url_keys:
                        value = result.get(key)
                        if isinstance(value, str) and value.startswith("http"):
                            return value
        
        # If it's a list
        if isinstance(data, list) and data:
            return self._extract_url_from_response(data[0])
        
        return None
    
    async def _download_stream(
        self,
        stream_url: str,
        output_path: Path,
        progress_callback: Optional[Callable],
        item: CourseItem,
    ) -> bool:
        """
        Download the video stream.
        
        Handles both:
        - M3U8/HLS streams (via ffmpeg)
        - Direct MP4 files (via HTTP download)
        
        Args:
            stream_url: Video stream URL
            output_path: Output file path
            progress_callback: Progress callback
            item: CourseItem
            
        Returns:
            True if successful
        """
        # Check stream type
        if ".m3u8" in stream_url or "m3u8" in stream_url.lower():
            self.logger.info("📺 Detected M3U8 stream, using ffmpeg")
            return await self._download_m3u8(stream_url, output_path, progress_callback)
        else:
            self.logger.info("📥 Direct video download")
            headers = self.pw_headers.copy()
            headers["Referer"] = "https://www.pw.live/"
            
            return await self._download_file(
                stream_url,
                output_path,
                item,
                progress_callback,
                extra_headers=headers,
            )
    
    async def _download_m3u8(
        self,
        m3u8_url: str,
        output_path: Path,
        progress_callback: Optional[Callable],
    ) -> bool:
        """
        Download M3U8/HLS stream using ffmpeg.
        
        Args:
            m3u8_url: M3U8 playlist URL
            output_path: Output file path
            progress_callback: Progress callback
            
        Returns:
            True if successful
        """
        try:
            # Build ffmpeg command
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-headers", f"Referer: https://www.pw.live/",
                "-i", m3u8_url,
                "-c", "copy",  # Copy without re-encoding
                "-bsf:a", "aac_adtstoasc",
                "-movflags", "+faststart",
                "-f", "mp4",
                str(output_path),
            ]
            
            self.logger.info("🎬 Starting ffmpeg download...")
            
            # Run ffmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Monitor progress from stderr
            async def monitor_progress():
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    
                    decoded = line.decode("utf-8", errors="replace")
                    
                    # Parse time progress
                    time_match = re.search(
                        r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})",
                        decoded,
                    )
                    if time_match and progress_callback:
                        hours = int(time_match.group(1))
                        minutes = int(time_match.group(2))
                        seconds = int(time_match.group(3))
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        
                        await progress_callback(
                            total_seconds,
                            0,
                            0,
                            None,
                        )
            
            # Wait for completion
            progress_task = asyncio.create_task(monitor_progress())
            return_code = await process.wait()
            await progress_task
            
            if return_code == 0:
                self.logger.info("✅ ffmpeg download completed")
                return True
            else:
                stderr = await process.stderr.read()
                self.logger.error(f"ffmpeg failed: {stderr.decode()[:200]}")
                return False
                
        except FileNotFoundError:
            self.logger.error(
                "ffmpeg not found! Install ffmpeg to download M3U8 streams.\n"
                "Ubuntu/Debian: sudo apt install ffmpeg\n"
                "Mac: brew install ffmpeg\n"
                "Windows: Download from https://ffmpeg.org/"
            )
            return False
        except Exception as e:
            self.logger.error(f"M3U8 download error: {e}")
            return False


# Need to import aiohttp here
import aiohttp
