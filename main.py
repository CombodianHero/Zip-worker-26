#!/usr/bin/env python3
"""
Saini Txt 2026 - Telegram Course Importer Bot
Main entry point for downloading and uploading course content.
"""

import asyncio
import signal
import sys
from pathlib import Path

from pyrogram import Client, filters, idle
from pyrogram.types import Message

from config import config
from database.repository import DatabaseRepository
from importer.importer import CourseImporter
from downloaders.selector import DownloaderSelector
from uploader.telegram_uploader import TelegramUploader
from queue.manager import QueueManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Initialize components
db = DatabaseRepository(config.DATABASE_URL)
importer = CourseImporter()
downloader = DownloaderSelector()

# Active queues per user
queues: dict = {}


async def start_command(client: Client, message: Message) -> None:
    """Handle /start command."""
    await message.reply_text(
        "📚 **Saini Txt 2026 - Course Importer Bot**\n\n"
        "Send me a course file:\n"
        "• **TXT file** - Course links\n"
        "• **ZIP file** - Course structure\n\n"
        "**Supported:** PW Videos, YouTube, PDF, MP4, M3U8\n\n"
        "Commands: /help /status /pause /resume /stop"
    )


async def help_command(client: Client, message: Message) -> None:
    """Handle /help command."""
    await message.reply_text(
        "📖 **Help**\n\n"
        "**TXT Format:**\n"
        "`Title:URL`\n\n"
        "**ZIP Structure:**\n"
        "Course.zip → Subject/ → Chapter/ → files.txt\n\n"
        "**PW Videos:**\n"
        "URLs with childId & parentId are auto-detected\n\n"
        "Set PW_TOKEN in .env for PW downloads"
    )


async def handle_document(client: Client, message: Message) -> None:
    """Handle document uploads."""
    user_id = message.from_user.id
    
    # Auth check
    if config.ALLOWED_USERS and user_id not in config.ALLOWED_USERS:
        await message.reply_text("❌ Not authorized")
        return
    
    doc = message.document
    file_name = doc.file_name or "unknown"
    
    if not file_name.lower().endswith((".txt", ".zip")):
        await message.reply_text("❌ Send .txt or .zip file only")
        return
    
    status_msg = await message.reply_text("📥 Downloading file...")
    
    try:
        # Download file
        file_path = config.TEMP_DIR / file_name
        await message.download(file_name=str(file_path))
        
        await status_msg.edit_text("📦 Importing course...")
        
        # Import
        items = await importer.import_course(file_path, config.TEMP_DIR)
        
        if not items:
            await status_msg.edit_text("❌ No valid items found")
            return
        
        # Create queue
        qm = QueueManager(db, downloader, None, config.DOWNLOADS_DIR)
        qm.add_items(items)
        queues[user_id] = qm
        
        await status_msg.edit_text(
            f"✅ **Imported:** {items[0].course}\n"
            f"📊 Items: {len(items)}\n\n"
            f"Starting processing...\n"
            f"/status for progress"
        )
        
        # Start processing
        uploader = TelegramUploader(client)
        qm.set_uploader(uploader)
        
        asyncio.create_task(
            process_queue(client, message.chat.id, status_msg, user_id)
        )
        
        file_path.unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")


async def process_queue(client, chat_id, status_msg, user_id):
    """Process queue in background."""
    qm = queues.get(user_id)
    if not qm:
        return
    
    try:
        await qm.process_all(
            progress_callback=lambda p: update_msg(status_msg, p)
        )
        
        stats = qm.get_stats()
        await status_msg.edit_text(
            f"✅ **Done!**\n"
            f"✅ {stats['completed']}/{stats['total']}\n"
            f"❌ Failed: {stats['failed']}"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)[:200]}")
    finally:
        if user_id in queues:
            del queues[user_id]


async def update_msg(msg, progress):
    """Update status message."""
    try:
        await msg.edit_text(
            f"⏳ Progress: {progress['completed']}/{progress['total']}"
        )
    except:
        pass


async def status_command(client, message):
    """Handle /status."""
    qm = queues.get(message.from_user.id)
    if qm:
        s = qm.get_stats()
        await message.reply_text(
            f"📊 {s['completed']}/{s['total']} | {s['status']}"
        )
    else:
        await message.reply_text("No active queue")


async def pause_command(client, message):
    """Handle /pause."""
    qm = queues.get(message.from_user.id)
    if qm:
        qm.pause()
        await message.reply_text("⏸️ Paused")
    else:
        await message.reply_text("No active queue")


async def resume_command(client, message):
    """Handle /resume."""
    qm = queues.get(message.from_user.id)
    if qm:
        qm.resume()
        await message.reply_text("▶️ Resumed")
    else:
        await message.reply_text("No active queue")


async def stop_command(client, message):
    """Handle /stop."""
    qm = queues.get(message.from_user.id)
    if qm:
        qm.stop()
        await message.reply_text("⏹️ Stopped")
        if message.from_user.id in queues:
            del queues[message.from_user.id]
    else:
        await message.reply_text("No active queue")


async def main():
    """Main entry point."""
    logger.info("Starting Saini Txt 2026 Bot...")
    
    try:
        config.validate()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    app = Client(
        "saini_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
    )
    
    # Register handlers
    app.add_handler(filters.command("start")(start_command))
    app.add_handler(filters.command("help")(help_command))
    app.add_handler(filters.command("status")(status_command))
    app.add_handler(filters.command("pause")(pause_command))
    app.add_handler(filters.command("resume")(resume_command))
    app.add_handler(filters.command("stop")(stop_command))
    app.add_handler(filters.document(handle_document))
    
    try:
        await app.start()
        me = await app.get_me()
        logger.info(f"Bot @{me.username} started!")
        logger.info(f"PW Token: {'✅' if config.PW_TOKEN else '❌'}")
        await idle()
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        await downloader.cleanup()
        await app.stop()
        db.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    asyncio.run(main())
