"""
SQLAlchemy ORM models for the database.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config import config

# Create base class for models
Base = declarative_base()


class CourseItemDB(Base):
    """
    Database model for course items.
    
    Stores all information about a course resource including
    download status, file paths, and metadata.
    """
    
    __tablename__ = "course_items"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Course structure
    course = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), default="", index=True)
    chapter = Column(String(500), default="")
    resource_type = Column(String(100), default="Resource", index=True)
    
    # Item details
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=False)
    index_num = Column(Integer, default=0)
    total = Column(Integer, default=0)
    
    # Processing status
    status = Column(
        String(50),
        default="pending",
        index=True,
        # Possible values: pending, downloading, downloaded, uploading, uploaded, completed, failed, cancelled
    )
    
    # File information
    local_file = Column(Text, nullable=True)  # Path to downloaded file
    thumbnail = Column(Text, nullable=True)   # Path to thumbnail
    extension = Column(String(20), nullable=True)
    downloader = Column(String(50), nullable=True)  # Which downloader was used
    file_size = Column(Integer, nullable=True)      # File size in bytes
    
    # Error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    
    # Additional data
    metadata_json = Column(JSON, nullable=True)  # Extra metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Priority
    priority = Column(Integer, default=0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "course": self.course,
            "subject": self.subject,
            "chapter": self.chapter,
            "resource_type": self.resource_type,
            "title": self.title,
            "url": self.url,
            "index_num": self.index_num,
            "total": self.total,
            "status": self.status,
            "local_file": self.local_file,
            "thumbnail": self.thumbnail,
            "extension": self.extension,
            "downloader": self.downloader,
            "file_size": self.file_size,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "priority": self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CourseItemDB":
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            course=data.get("course", ""),
            subject=data.get("subject", ""),
            chapter=data.get("chapter", ""),
            resource_type=data.get("resource_type", "Resource"),
            title=data.get("title", ""),
            url=data.get("url", ""),
            index_num=data.get("index_num", data.get("index", 0)),
            total=data.get("total", 0),
            status=data.get("status", "pending"),
            local_file=data.get("local_file"),
            thumbnail=data.get("thumbnail"),
            extension=data.get("extension"),
            downloader=data.get("downloader"),
            file_size=data.get("file_size"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message"),
            metadata_json=data.get("metadata_json"),
            priority=data.get("priority", 0),
        )
    
    def __repr__(self):
        return f"<CourseItemDB(id={self.id}, title='{self.title[:30]}', status='{self.status}')>"


class UserSettings(Base):
    """User-specific settings."""
    
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    
    # Upload preferences
    upload_as_video = Column(Boolean, default=True)
    add_thumbnails = Column(Boolean, default=True)
    add_captions = Column(Boolean, default=True)
    
    # Download preferences
    max_concurrent = Column(Integer, default=1)
    preferred_quality = Column(String(20), default="720p")
    
    # Limits
    daily_limit = Column(Integer, default=100)
    downloaded_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.now)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ProcessingLog(Base):
    """Log of processing activities."""
    
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, nullable=True, index=True)
    action = Column(String(50), nullable=False)  # download, upload, error, retry, etc.
    status = Column(String(20), nullable=False)   # success, failed, in_progress
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)


# Database engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        db_path = config.DATABASE_DIR / "courses.db"
        _engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session() -> Session:
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Initialize database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ Database initialized successfully")
