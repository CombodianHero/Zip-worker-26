#!/usr/bin/env python3
"""
COMPLETE SETUP SCRIPT - Creates ALL files for Saini-Txt-2026 bot.
Run this script once and everything will be created correctly.
"""

import os
import sys
from pathlib import Path

# ==================== SETUP ====================

BASE_DIR = Path("Saini-Txt-2026")
BASE_DIR.mkdir(exist_ok=True)

# Create ALL directories
DIRS = [
    "database",
    "models", 
    "downloaders",
    "importer",
    "utils",
    "downloads",
    "temp",
    "logs",
]

for d in DIRS:
    (BASE_DIR / d).mkdir(exist_ok=True)

print(f"📁 Creating project at: {BASE_DIR.absolute()}\n")

# ==================== ALL FILES ====================

files_to_create = {}

# ==================== .env.example ====================
files_to_create[".env.example"] = """API_ID=12345678
API_HASH=your_api_hash_here
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789
ALLOWED_USERS=123456789
PW_TOKEN=your_pw_token_here
PW_API_URL=https://anonymouspwplayeer-2038df9c1dbd.herokuapp.com
MAX_CONCURRENT_DOWNLOADS=1
LOG_LEVEL=INFO
"""

# ==================== requirements.txt ====================
files_to_create["requirements.txt"] = """pyrogram>=2.0.106
tgcrypto>=1.2.5
python-dotenv>=1.0.0
aiohttp>=3.9.1
aiofiles>=23.2.1
SQLAlchemy>=2.0.25
requests>=2.31.0
"""

# ==================== config.py ====================
files_to_create["config.py"] = '''"""Configuration module."""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    API_ID: int = field(default_factory=lambda: int(os.getenv("API_ID", "0")))
    API_HASH: str = field(default_factory=lambda: os.getenv("API_HASH", ""))
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_IDS: List[int] = field(default_factory=lambda: [int(uid.strip()) for uid in os.getenv("ADMIN_IDS", "").split(",") if uid.strip()])
    ALLOWED_USERS: List[int] = field(default_factory=lambda: [int(uid.strip()) for uid in os.getenv("ALLOWED_USERS", "").split(",") if uid.strip()])
    PW_TOKEN: str = field(default_factory=lambda: os.getenv("PW_TOKEN", ""))
    PW_API_URL: str = field(default_factory=lambda: os.getenv("PW_API_URL", "https://anonymouspwplayeer-2038df9c1dbd.herokuapp.com"))
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    DOWNLOADS_DIR: Path = field(default_factory=lambda: Path("downloads"))
    TEMP_DIR: Path = field(default_factory=lambda: Path("temp"))
    LOGS_DIR: Path = field(default_factory=lambda: Path("logs"))
    DATABASE_DIR: Path = field(default_factory=lambda: Path("database"))
    MAX_CONCURRENT_DOWNLOADS: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "1")))
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    def __post_init__(self):
        for d in [self.DOWNLOADS_DIR, self.TEMP_DIR, self.LOGS_DIR, self.DATABASE_DIR]:
            d.mkdir(exist_ok=True)
    
    def validate(self):
        missing = []
        if not self.API_ID: missing.append("API_ID")
        if not self.API_HASH: missing.append("API_HASH")
        if not self.BOT_TOKEN: missing.append("BOT_TOKEN")
        if missing:
            raise ValueError(f"Missing config: {', '.join(missing)}")
        return True

config = Config()
'''

# ==================== database/__init__.py ====================
files_to_create["database/__init__.py"] = """from database.repository import DatabaseRepository
__all__ = ["DatabaseRepository"]
"""

# ==================== database/repository.py ====================
files_to_create["database/repository.py"] = '''"""Database repository - simple SQLite operations."""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import config

class DatabaseRepository:
    """Simple SQLite database for course items."""
    
    def __init__(self):
        self.db_path = config.DATABASE_DIR / "courses.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course TEXT NOT NULL,
                subject TEXT DEFAULT '',
                chapter TEXT DEFAULT '',
                resource_type TEXT DEFAULT 'Resource',
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                index_num INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                local_file TEXT,
                extension TEXT,
                downloader TEXT,
                file_size INTEGER,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                action TEXT,
                status TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def insert(self, data: dict) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO course_items (course, subject, chapter, resource_type, title, url, index_num, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("course", ""),
            data.get("subject", ""),
            data.get("chapter", ""),
            data.get("resource_type", "Resource"),
            data.get("title", ""),
            data.get("url", ""),
            data.get("index", 0),
            data.get("total", 0),
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_batch(self, items: List[dict]) -> List[int]:
        cursor = self.conn.cursor()
        ids = []
        for data in items:
            cursor.execute("""
                INSERT INTO course_items (course, subject, chapter, resource_type, title, url, index_num, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("course", ""),
                data.get("subject", ""),
                data.get("chapter", ""),
                data.get("resource_type", "Resource"),
                data.get("title", ""),
                data.get("url", ""),
                data.get("index", 0),
                data.get("total", 0),
            ))
            ids.append(cursor.lastrowid)
        self.conn.commit()
        return ids
    
    def get_all(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM course_items ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_by_id(self, item_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM course_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM course_items WHERE status = ? ORDER BY id LIMIT ?",
            (status, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_pending(self, limit: int = 100) -> List[Dict]:
        return self.get_by_status("pending", limit)
    
    def get_failed(self, limit: int = 50) -> List[Dict]:
        return self.get_by_status("failed", limit)
    
    def update_status(self, item_id: int, status: str, **kwargs) -> bool:
        cursor = self.conn.cursor()
        updates = ["status = ?"]
        params = [status]
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            params.append(value)
        
        if status in ("completed", "uploaded", "failed"):
            updates.append("completed_at = CURRENT_TIMESTAMP")
        
        if status == "failed":
            updates.append("retry_count = retry_count + 1")
        
        params.append(item_id)
        
        cursor.execute(
            f"UPDATE course_items SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, int]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) as uploaded,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'downloading' THEN 1 ELSE 0 END) as downloading
            FROM course_items
        """)
        row = cursor.fetchone()
        return dict(row) if row else {}
    
    def url_exists(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM course_items WHERE url = ?", (url,))
        return cursor.fetchone() is not None
    
    def delete_item(self, item_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM course_items WHERE id = ?", (item_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def clear_course(self, course: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM course_items WHERE course = ?", (course,))
        self.conn.commit()
        return cursor.rowcount
    
    def log_action(self, item_id: int, action: str, status: str, message: str = None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO processing_logs (item_id, action, status, message) VALUES (?, ?, ?, ?)",
            (item_id, action, status, message)
        )
        self.conn.commit()
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM processing_logs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        if self.conn:
            self.conn.close()
'''

# ==================== models/__init__.py ====================
files_to_create["models/__init__.py"] = """from models.course_item import CourseItem
__all__ = ["CourseItem"]
"""

# ==================== models/course_item.py ====================
files_to_create["models/course_item.py"] = '''"""CourseItem data model."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

@dataclass
class CourseItem:
    course: str
    subject: str
    chapter: str
    resource_type: str
    title: str
    url: str
    index: int
    total: int
    id: Optional[int] = None
    status: str = "pending"
    local_file: Optional[Path] = None
    extension: Optional[str] = None
    downloader: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def formatted_index(self) -> str:
        if self.total <= 0:
            return str(self.index)
        padding = 2 if self.total < 100 else 3
        return f"{self.index:0{padding}d}"
    
    @property
    def is_pw_video(self) -> bool:
        return "childId" in self.url and "parentId" in self.url
    
    def to_dict(self) -> dict:
        return {
            "course": self.course,
            "subject": self.subject,
            "chapter": self.chapter,
            "resource_type": self.resource_type,
            "title": self.title,
            "url": self.url,
            "index": self.index,
            "total": self.total,
            "status": self.status,
        }
'''

# ==================== downloaders/__init__.py ====================
files_to_create["downloaders/__init__.py"] = """from downloaders.pw_downloader import PWDownloader
from downloaders.selector import DownloaderSelector
__all__ = ["PWDownloader", "DownloaderSelector"]
"""

# ==================== downloaders/pw_downloader.py ====================
files_to_create["downloaders/pw_downloader.py"] = '''"""Physics Wallah Video Downloader."""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from config import config

logger = logging.getLogger(__name__)

class PWDownloader:
    """Downloads PW videos via proxy API."""
    
    def __init__(self):
        self.token = config.PW_TOKEN
        self.api_url = config.PW_API_URL.rstrip("/")
    
    def can_handle(self, url: str) -> bool:
        if "childId" in url and "parentId" in url:
            return True
        if "pw.live" in url.lower():
            return True
        return False
    
    async def download(self, url: str, output_path: Path) -> bool:
        if not self.token:
            logger.error("PW_TOKEN not set")
            return False
        
        try:
            stream_url = await self._get_stream_url(url)
            if not stream_url:
                return False
            return await self._download_stream(stream_url, output_path)
        except Exception as e:
            logger.error(f"PW download failed: {e}")
            return False
    
    async def _get_stream_url(self, original_url: str) -> Optional[str]:
        import aiohttp
        
        api_url = f"{self.api_url}/pw"
        params = {"url": original_url, "token": self.token}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://www.pw.live",
            "Referer": "https://www.pw.live/",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params, headers=headers, timeout=30) as resp:
                    if resp.status != 200:
                        return None
                    
                    try:
                        data = await resp.json()
                    except:
                        text = await resp.text()
                        if text.startswith("http"):
                            return text.strip()
                        return None
                    
                    return self._extract_url(data)
        except Exception as e:
            logger.error(f"API failed: {e}")
            return None
    
    def _extract_url(self, data) -> Optional[str]:
        if isinstance(data, str) and data.startswith("http"):
            return data
        if isinstance(data, dict):
            for key in ["url", "video_url", "stream_url", "data"]:
                val = data.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    return val
                if isinstance(val, dict):
                    result = self._extract_url(val)
                    if result:
                        return result
        return None
    
    async def _download_stream(self, url: str, output_path: Path) -> bool:
        import aiohttp
        
        if ".m3u8" in url:
            return await self._download_m3u8(url, output_path)
        
        try:
            headers = {"Referer": "https://www.pw.live/"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024*1024):
                                f.write(chunk)
                        return output_path.exists() and output_path.stat().st_size > 0
            return False
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    async def _download_m3u8(self, url: str, output_path: Path) -> bool:
        try:
            cmd = ["ffmpeg", "-y", "-i", url, "-c", "copy", str(output_path)]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            return proc.returncode == 0 and output_path.exists()
        except FileNotFoundError:
            logger.error("ffmpeg not installed")
            return False
        except Exception as e:
            logger.error(f"M3U8 failed: {e}")
            return False
'''

# ==================== downloaders/selector.py ====================
files_to_create["downloaders/selector.py"] = '''"""Downloader selector."""
import asyncio
import logging
from pathlib import Path
from typing import Tuple, Optional
from downloaders.pw_downloader import PWDownloader
from config import config

logger = logging.getLogger(__name__)

class DownloaderSelector:
    def __init__(self):
        self.pw = PWDownloader()
        self._sem = asyncio.Semaphore(config.MAX_CONCURRENT_DOWNLOADS)
    
    async def download(self, url: str, output_path: Path) -> Tuple[bool, Optional[str]]:
        async with self._sem:
            if self.pw.can_handle(url):
                logger.info(f"Using PW downloader")
                ok = await self.pw.download(url, output_path)
                return (ok, None if ok else "PW download failed")
            
            # Direct download
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, "wb") as f:
                                async for chunk in resp.content.iter_chunked(1024*1024):
                                    f.write(chunk)
                            ok = output_path.exists() and output_path.stat().st_size > 0
                            return (ok, None if ok else "Empty file")
                return (False, f"HTTP {resp.status}")
            except Exception as e:
                return (False, str(e))
'''

# ==================== importer/__init__.py ====================
files_to_create["importer/__init__.py"] = """from importer.importer import CourseImporter
__all__ = ["CourseImporter"]
"""

# ==================== importer/importer.py ====================
files_to_create["importer/importer.py"] = '''"""Course importer for TXT and ZIP files."""
import logging
from pathlib import Path
from typing import List
from models.course_item import CourseItem

logger = logging.getLogger(__name__)

class CourseImporter:
    async def import_file(self, file_path: Path) -> List[CourseItem]:
        if file_path.suffix.lower() == ".txt":
            return self._import_txt(file_path)
        elif file_path.suffix.lower() == ".zip":
            return await self._import_zip(file_path)
        else:
            raise ValueError(f"Unsupported: {file_path.suffix}")
    
    def _import_txt(self, file_path: Path) -> List[CourseItem]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        parsed = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for sep in [":https://", ":http://"]:
                if sep in line:
                    parts = line.rsplit(sep, 1)
                    title = parts[0].strip()
                    url = sep[1:] + parts[1].strip()
                    if url.startswith("http"):
                        parsed.append((title, url))
                    break
        
        course = file_path.stem
        total = len(parsed)
        items = []
        for idx, (title, url) in enumerate(parsed, 1):
            items.append(CourseItem(
                course=course, subject="", chapter="",
                resource_type=self._detect_type(file_path.stem),
                title=title, url=url, index=idx, total=total,
            ))
        
        logger.info(f"Imported {len(items)} from {file_path.name}")
        return items
    
    async def _import_zip(self, file_path: Path) -> List[CourseItem]:
        import zipfile, tempfile
        items = []
        course = file_path.stem
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(file_path) as zf:
                zf.extractall(tmpdir)
            
            tmp = Path(tmpdir)
            for txt_file in tmp.rglob("*.txt"):
                with open(txt_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                parsed = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    for sep in [":https://", ":http://"]:
                        if sep in line:
                            parts = line.rsplit(sep, 1)
                            title = parts[0].strip()
                            url = sep[1:] + parts[1].strip()
                            if url.startswith("http"):
                                parsed.append((title, url))
                            break
                
                rel = txt_file.relative_to(tmp)
                parts = rel.parts
                subject = parts[0] if parts else ""
                chapter = " > ".join(parts[1:-1]) if len(parts) > 2 else ""
                
                total = len(parsed)
                for idx, (title, url) in enumerate(parsed, 1):
                    items.append(CourseItem(
                        course=course, subject=subject, chapter=chapter,
                        resource_type=self._detect_type(txt_file.stem),
                        title=title, url=url, index=idx, total=total,
                    ))
        
        logger.info(f"Imported {len(items)} from {file_path.name}")
        return items
    
    def _detect_type(self, name: str) -> str:
        name = "".join(c for c in name.lower() if c.isalnum())
        types = {"videos": "Lecture Video", "notes": "Lecture Notes",
                 "dppvideos": "DPP Video", "dppnotes": "DPP Notes",
                 "assignment": "Assignment", "solutions": "Solution",
                 "tests": "Test", "pyq": "PYQ"}
        for k, v in types.items():
            if k in name:
                return v
        return "Resource"
'''

# ==================== utils/__init__.py ====================
files_to_create["utils/__init__.py"] = ""

# ==================== main.py ====================
files_to_create["main.py"] = '''#!/usr/bin/env python3
"""Saini Txt 2026 - Main Bot Entry Point"""
import asyncio, signal, sys, logging
from pathlib import Path
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from config import config
from database.repository import DatabaseRepository
from importer.importer import CourseImporter
from downloaders.selector import DownloaderSelector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

db = DatabaseRepository()
importer = CourseImporter()
downloader = DownloaderSelector()

async def start(client: Client, msg: Message):
    await msg.reply("📚 **Saini Txt 2026 Bot**\\n\\nSend .txt or .zip file to start.\\n\\nCommands: /help /status")

async def help_cmd(client: Client, msg: Message):
    await msg.reply("📖 **Help**\\n\\n**TXT Format:**\\n`Title:URL`\\n\\n**PW Videos:** Auto-detected (childId/parentId)")

async def status_cmd(client: Client, msg: Message):
    stats = db.get_stats()
    await msg.reply(f"📊 Total:{stats.get('total',0)} | ✅:{stats.get('completed',0)} | ⏳:{stats.get('pending',0)} | ❌:{stats.get('failed',0)}")

async def handle_file(client: Client, msg: Message):
    uid = msg.from_user.id
    if config.ALLOWED_USERS and uid not in config.ALLOWED_USERS:
        await msg.reply("❌ Not authorized")
        return
    
    doc = msg.document
    fname = doc.file_name or "unknown"
    if not fname.lower().endswith((".txt", ".zip")):
        await msg.reply("❌ Send .txt or .zip only")
        return
    
    status = await msg.reply("📥 Downloading...")
    try:
        fp = config.TEMP_DIR / fname
        await msg.download(file_name=str(fp))
        await status.edit("📦 Importing...")
        
        items = await importer.import_file(fp)
        if not items:
            await status.edit("❌ No items found")
            fp.unlink(missing_ok=True)
            return
        
        for item in items:
            db.insert(item.to_dict())
        
        await status.edit(f"✅ {items[0].course}\\n📊 {len(items)} items\\n🔄 Processing...")
        
        ok_count = 0
        fail_count = 0
        
        for i, item in enumerate(items, 1):
            try:
                await status.edit(f"⬇️ [{i}/{len(items)}] {item.title[:40]}...")
                ext = "mp4" if item.is_pw_video else "bin"
                out = config.DOWNLOADS_DIR / f"{item.formatted_index}_{item.title[:30]}.{ext}"
                out.parent.mkdir(parents=True, exist_ok=True)
                
                success, err = await downloader.download(item.url, out)
                
                if success and out.exists() and out.stat().st_size > 0:
                    await status.edit(f"⬆️ [{i}/{len(items)}] Uploading...")
                    cap = f"📚 {item.title}\\n📊 {i}/{len(items)}\\n📦 {item.resource_type}"
                    
                    try:
                        if out.suffix in [".mp4", ".mkv"]:
                            await client.send_video(msg.chat.id, str(out), caption=cap, supports_streaming=True)
                        else:
                            await client.send_document(msg.chat.id, str(out), caption=cap)
                        db.update_status(item.id, "completed")
                        ok_count += 1
                    except Exception as e:
                        db.update_status(item.id, "failed", error_message=str(e))
                        fail_count += 1
                    
                    out.unlink(missing_ok=True)
                else:
                    db.update_status(item.id, "failed", error_message=err or "Download failed")
                    fail_count += 1
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed: {e}")
                fail_count += 1
        
        await status.edit(f"✅ Done!\\n✅ {ok_count} | ❌ {fail_count} | 📊 {len(items)}")
        fp.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit(f"❌ {str(e)[:200]}")

async def main():
    logger.info("Starting bot...")
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    app = Client("saini_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)
    app.add_handler(filters.command("start")(start))
    app.add_handler(filters.command("help")(help_cmd))
    app.add_handler(filters.command("status")(status_cmd))
    app.add_handler(filters.document(handle_file))
    
    try:
        await app.start()
        me = await app.get_me()
        logger.info(f"✅ Bot @{me.username} started!")
        logger.info(f"PW Token: {'✅' if config.PW_TOKEN else '❌'}")
        await idle()
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await app.stop()
        db.close()
        logger.info("Done")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    asyncio.run(main())
'''


# ==================== WRITE ALL FILES ====================
print("Creating files...\n")

for filepath, content in files_to_create.items():
    full_path = BASE_DIR / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {filepath}")

# ==================== VERIFY ====================
print("\n" + "="*50)
print("Verifying installation...")
print("="*50)

errors = []

# Check all files exist
for filepath in files_to_create:
    full_path = BASE_DIR / filepath
    if not full_path.exists():
        errors.append(f"❌ Missing: {filepath}")

# Check imports work
import_check = """
import sys
sys.path.insert(0, '.')
try:
    from config import config
    print('✅ config.py')
except Exception as e:
    print(f'❌ config.py: {e}')

try:
    from database.repository import DatabaseRepository
    print('✅ database/repository.py')
except Exception as e:
    print(f'❌ database/repository.py: {e}')

try:
    from models.course_item import CourseItem
    print('✅ models/course_item.py')
except Exception as e:
    print(f'❌ models/course_item.py: {e}')

try:
    from downloaders.pw_downloader import PWDownloader
    print('✅ downloaders/pw_downloader.py')
except Exception as e:
    print(f'❌ downloaders/pw_downloader.py: {e}')

try:
    from downloaders.selector import DownloaderSelector
    print('✅ downloaders/selector.py')
except Exception as e:
    print(f'❌ downloaders/selector.py: {e}')

try:
    from importer.importer import CourseImporter
    print('✅ importer/importer.py')
except Exception as e:
    print(f'❌ importer/importer.py: {e}')
"""

print("\nChecking imports...")
os.chdir(str(BASE_DIR))
exec(import_check)

if errors:
    print("\n❌ Errors found:")
    for e in errors:
        print(f"  {e}")
else:
    print("\n✅ All files created successfully!")

print(f"\n📁 Project location: {BASE_DIR.absolute()}")
print("\nNext steps:")
print("  cd Saini-Txt-2026")
print("  cp .env.example .env")
print("  nano .env  # Edit with your credentials")
print("  pip install -r requirements.txt")
print("  python main.py")
