"""
Database repository - high-level database operations.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from database.models import (
    CourseItemDB,
    UserSettings,
    ProcessingLog,
    get_session,
    init_db,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseRepository:
    """
    High-level repository for database operations.
    
    Provides methods for:
    - CRUD operations on course items
    - Statistics and reporting
    - Queue management
    - User settings
    - Processing logs
    """
    
    def __init__(self):
        """Initialize database and create tables."""
        init_db()
        self.logger = logger
    
    # ==================== Course Items ====================
    
    def insert_item(self, data: dict) -> int:
        """
        Insert a new course item.
        
        Args:
            data: Item data dictionary
            
        Returns:
            ID of inserted item
        """
        session = get_session()
        try:
            item = CourseItemDB.from_dict(data)
            session.add(item)
            session.commit()
            item_id = item.id
            self.logger.debug(f"Inserted item: {item_id} - {item.title[:50]}")
            return item_id
        except Exception as e:
            session.rollback()
            self.logger.error(f"Insert failed: {e}")
            raise
        finally:
            session.close()
    
    def insert_items(self, items: List[dict]) -> List[int]:
        """
        Insert multiple course items.
        
        Args:
            items: List of item data dictionaries
            
        Returns:
            List of inserted IDs
        """
        session = get_session()
        ids = []
        try:
            for data in items:
                item = CourseItemDB.from_dict(data)
                session.add(item)
                session.flush()
                ids.append(item.id)
            session.commit()
            self.logger.info(f"Inserted {len(ids)} items")
            return ids
        except Exception as e:
            session.rollback()
            self.logger.error(f"Batch insert failed: {e}")
            raise
        finally:
            session.close()
    
    def get_item(self, item_id: int) -> Optional[Dict]:
        """
        Get a single item by ID.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item dictionary or None
        """
        session = get_session()
        try:
            item = session.query(CourseItemDB).filter_by(id=item_id).first()
            return item.to_dict() if item else None
        finally:
            session.close()
    
    def get_item_by_url(self, url: str) -> Optional[Dict]:
        """
        Check if URL already exists.
        
        Args:
            url: Download URL
            
        Returns:
            Item dictionary or None
        """
        session = get_session()
        try:
            item = session.query(CourseItemDB).filter_by(url=url).first()
            return item.to_dict() if item else None
        finally:
            session.close()
    
    def get_items_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """
        Get items by status.
        
        Args:
            status: Item status (pending, completed, failed, etc.)
            limit: Maximum items to return
            
        Returns:
            List of item dictionaries
        """
        session = get_session()
        try:
            items = (
                session.query(CourseItemDB)
                .filter_by(status=status)
                .order_by(CourseItemDB.priority.asc(), CourseItemDB.id.asc())
                .limit(limit)
                .all()
            )
            return [item.to_dict() for item in items]
        finally:
            session.close()
    
    def get_pending_items(self, limit: int = 10) -> List[Dict]:
        """
        Get pending items for processing.
        
        Args:
            limit: Maximum items
            
        Returns:
            List of pending item dictionaries
        """
        return self.get_items_by_status("pending", limit)
    
    def get_failed_items(self, limit: int = 50) -> List[Dict]:
        """
        Get failed items that can be retried.
        
        Args:
            limit: Maximum items
            
        Returns:
            List of failed item dictionaries
        """
        session = get_session()
        try:
            items = (
                session.query(CourseItemDB)
                .filter(
                    and_(
                        CourseItemDB.status == "failed",
                        CourseItemDB.retry_count < CourseItemDB.max_retries,
                    )
                )
                .order_by(CourseItemDB.retry_count.asc())
                .limit(limit)
                .all()
            )
            return [item.to_dict() for item in items]
        finally:
            session.close()
    
    def get_items_by_course(self, course: str) -> List[Dict]:
        """
        Get all items for a course.
        
        Args:
            course: Course name
            
        Returns:
            List of item dictionaries
        """
        session = get_session()
        try:
            items = (
                session.query(CourseItemDB)
                .filter_by(course=course)
                .order_by(CourseItemDB.id.asc())
                .all()
            )
            return [item.to_dict() for item in items]
        finally:
            session.close()
    
    def update_item(self, item_id: int, **kwargs) -> bool:
        """
        Update item fields.
        
        Args:
            item_id: Item ID
            **kwargs: Fields to update
            
        Returns:
            True if successful
        """
        session = get_session()
        try:
            item = session.query(CourseItemDB).filter_by(id=item_id).first()
            if not item:
                return False
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            # Update timestamp
            item.updated_at = datetime.now()
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"Update failed for item {item_id}: {e}")
            return False
        finally:
            session.close()
    
    def update_status(
        self,
        item_id: int,
        status: str,
        error_message: str = None,
        local_file: str = None,
        extension: str = None,
        downloader: str = None,
        file_size: int = None,
    ) -> bool:
        """
        Update item processing status.
        
        Args:
            item_id: Item ID
            status: New status
            error_message: Error message if failed
            local_file: Path to downloaded file
            extension: File extension
            downloader: Downloader used
            file_size: File size in bytes
            
        Returns:
            True if successful
        """
        updates = {"status": status}
        
        if error_message:
            updates["error_message"] = error_message
        
        if local_file:
            updates["local_file"] = local_file
        
        if extension:
            updates["extension"] = extension
        
        if downloader:
            updates["downloader"] = downloader
        
        if file_size:
            updates["file_size"] = file_size
        
        # Set timestamps
        if status == "downloading":
            updates["started_at"] = datetime.now()
        elif status in ("completed", "uploaded", "failed"):
            updates["completed_at"] = datetime.now()
        
        # Increment retry count on failure
        if status == "failed":
            session = get_session()
            try:
                item = session.query(CourseItemDB).filter_by(id=item_id).first()
                if item:
                    updates["retry_count"] = item.retry_count + 1
            finally:
                session.close()
        
        return self.update_item(item_id, **updates)
    
    def delete_item(self, item_id: int) -> bool:
        """
        Delete an item.
        
        Args:
            item_id: Item ID
            
        Returns:
            True if deleted
        """
        session = get_session()
        try:
            item = session.query(CourseItemDB).filter_by(id=item_id).first()
            if item:
                session.delete(item)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"Delete failed: {e}")
            return False
        finally:
            session.close()
    
    def delete_course(self, course: str) -> int:
        """
        Delete all items for a course.
        
        Args:
            course: Course name
            
        Returns:
            Number of deleted items
        """
        session = get_session()
        try:
            count = (
                session.query(CourseItemDB)
                .filter_by(course=course)
                .delete()
            )
            session.commit()
            self.logger.info(f"Deleted {count} items for course: {course}")
            return count
        except Exception as e:
            session.rollback()
            self.logger.error(f"Course delete failed: {e}")
            return 0
        finally:
            session.close()
    
    def url_exists(self, url: str) -> bool:
        """
        Check if URL already in database.
        
        Args:
            url: URL to check
            
        Returns:
            True if exists
        """
        session = get_session()
        try:
            exists = session.query(CourseItemDB).filter_by(url=url).first()
            return exists is not None
        finally:
            session.close()
    
    # ==================== Statistics ====================
    
    def get_stats(self, course: str = None) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Args:
            course: Optional course filter
            
        Returns:
            Dictionary with statistics
        """
        session = get_session()
        try:
            query = session.query(CourseItemDB)
            
            if course:
                query = query.filter_by(course=course)
            
            total = query.count()
            completed = query.filter_by(status="completed").count()
            uploaded = query.filter_by(status="uploaded").count()
            failed = query.filter_by(status="failed").count()
            pending = query.filter_by(status="pending").count()
            downloading = query.filter_by(status="downloading").count()
            
            # Total file size
            total_size = session.query(
                func.sum(CourseItemDB.file_size)
            ).filter(
                CourseItemDB.file_size.isnot(None)
            )
            if course:
                total_size = total_size.filter_by(course=course)
            total_size = total_size.scalar() or 0
            
            # Courses list
            courses = (
                session.query(
                    CourseItemDB.course,
                    func.count(CourseItemDB.id).label("count"),
                )
                .group_by(CourseItemDB.course)
                .all()
            )
            
            return {
                "total": total,
                "completed": completed,
                "uploaded": uploaded,
                "failed": failed,
                "pending": pending,
                "downloading": downloading,
                "total_size": total_size,
                "total_size_formatted": self._format_size(total_size),
                "courses": [
                    {"name": c[0], "count": c[1]} for c in courses
                ],
            }
        finally:
            session.close()
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """
        Get today's statistics.
        
        Returns:
            Dictionary with daily stats
        """
        session = get_session()
        try:
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            downloaded_today = (
                session.query(CourseItemDB)
                .filter(
                    and_(
                        CourseItemDB.status.in_(["completed", "uploaded"]),
                        CourseItemDB.completed_at >= today_start,
                    )
                )
                .count()
            )
            
            failed_today = (
                session.query(CourseItemDB)
                .filter(
                    and_(
                        CourseItemDB.status == "failed",
                        CourseItemDB.completed_at >= today_start,
                    )
                )
                .count()
            )
            
            total_size_today = (
                session.query(func.sum(CourseItemDB.file_size))
                .filter(
                    and_(
                        CourseItemDB.file_size.isnot(None),
                        CourseItemDB.completed_at >= today_start,
                    )
                )
                .scalar() or 0
            )
            
            return {
                "date": today.isoformat(),
                "downloaded": downloaded_today,
                "failed": failed_today,
                "total_size": total_size_today,
                "total_size_formatted": self._format_size(total_size_today),
            }
        finally:
            session.close()
    
    # ==================== Queue Operations ====================
    
    def get_queue_size(self) -> int:
        """Get number of pending items."""
        return self.get_stats()["pending"]
    
    def get_next_batch(self, batch_size: int = 10) -> List[Dict]:
        """
        Get next batch of items to process.
        
        Args:
            batch_size: Number of items
            
        Returns:
            List of item dictionaries
        """
        session = get_session()
        try:
            items = (
                session.query(CourseItemDB)
                .filter_by(status="pending")
                .order_by(
                    CourseItemDB.priority.asc(),
                    CourseItemDB.id.asc(),
                )
                .limit(batch_size)
                .all()
            )
            
            # Mark as downloading
            for item in items:
                item.status = "downloading"
                item.started_at = datetime.now()
            
            session.commit()
            
            return [item.to_dict() for item in items]
        except Exception as e:
            session.rollback()
            self.logger.error(f"Get next batch failed: {e}")
            return []
        finally:
            session.close()
    
    def reset_stalled_items(self, minutes: int = 30) -> int:
        """
        Reset items stuck in 'downloading' status.
        
        Args:
            minutes: Stalled threshold in minutes
            
        Returns:
            Number of reset items
        """
        session = get_session()
        try:
            threshold = datetime.now() - timedelta(minutes=minutes)
            
            stalled = (
                session.query(CourseItemDB)
                .filter(
                    and_(
                        CourseItemDB.status == "downloading",
                        CourseItemDB.started_at < threshold,
                    )
                )
                .all()
            )
            
            count = 0
            for item in stalled:
                item.status = "pending"
                count += 1
            
            session.commit()
            
            if count > 0:
                self.logger.info(f"Reset {count} stalled items")
            
            return count
        except Exception as e:
            session.rollback()
            self.logger.error(f"Reset stalled failed: {e}")
            return 0
        finally:
            session.close()
    
    # ==================== Processing Logs ====================
    
    def log_action(
        self,
        item_id: int,
        action: str,
        status: str,
        message: str = None,
        details: dict = None,
    ) -> None:
        """
        Log a processing action.
        
        Args:
            item_id: Item ID
            action: Action type (download, upload, etc.)
            status: Status (success, failed, etc.)
            message: Log message
            details: Additional details
        """
        session = get_session()
        try:
            log = ProcessingLog(
                item_id=item_id,
                action=action,
                status=status,
                message=message,
                details=details,
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Log failed: {e}")
        finally:
            session.close()
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """
        Get recent processing logs.
        
        Args:
            limit: Maximum logs
            
        Returns:
            List of log dictionaries
        """
        session = get_session()
        try:
            logs = (
                session.query(ProcessingLog)
                .order_by(ProcessingLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": log.id,
                    "item_id": log.item_id,
                    "action": log.action,
                    "status": log.status,
                    "message": log.message,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        finally:
            session.close()
    
    # ==================== User Settings ====================
    
    def get_user_settings(self, user_id: int) -> Dict:
        """
        Get settings for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Settings dictionary
        """
        session = get_session()
        try:
            settings = (
                session.query(UserSettings)
                .filter_by(user_id=user_id)
                .first()
            )
            
            if settings:
                return {
                    "user_id": settings.user_id,
                    "upload_as_video": settings.upload_as_video,
                    "add_thumbnails": settings.add_thumbnails,
                    "add_captions": settings.add_captions,
                    "max_concurrent": settings.max_concurrent,
                    "preferred_quality": settings.preferred_quality,
                    "daily_limit": settings.daily_limit,
                    "downloaded_today": settings.downloaded_today,
                }
            
            # Return defaults
            return {
                "user_id": user_id,
                "upload_as_video": True,
                "add_thumbnails": True,
                "add_captions": True,
                "max_concurrent": 1,
                "preferred_quality": "720p",
                "daily_limit": 100,
                "downloaded_today": 0,
            }
        finally:
            session.close()
    
    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """
        Update user settings.
        
        Args:
            user_id: Telegram user ID
            **kwargs: Settings to update
            
        Returns:
            True if successful
        """
        session = get_session()
        try:
            settings = (
                session.query(UserSettings)
                .filter_by(user_id=user_id)
                .first()
            )
            
            if not settings:
                settings = UserSettings(user_id=user_id)
                session.add(settings)
            
            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            settings.updated_at = datetime.now()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"Settings update failed: {e}")
            return False
        finally:
            session.close()
    
    # ==================== Utilities ====================
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        if size is None or size == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def vacuum(self) -> None:
        """Optimize database (SQLite vacuum)."""
        session = get_session()
        try:
            session.execute("VACUUM")
            self.logger.info("Database vacuumed")
        except Exception as e:
            self.logger.error(f"Vacuum failed: {e}")
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connection."""
        # SQLAlchemy handles connection pooling
        pass
    
    def backup(self, backup_path: str = None) -> bool:
        """
        Backup database to file.
        
        Args:
            backup_path: Path for backup file
            
        Returns:
            True if successful
        """
        import shutil
        from datetime import datetime
        
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config.DATABASE_DIR / f"backup_{timestamp}.db"
        
        try:
            db_path = config.DATABASE_DIR / "courses.db"
            shutil.copy2(db_path, backup_path)
            self.logger.info(f"Database backed up to: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            return False
