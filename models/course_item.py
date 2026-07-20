"""
CourseItem model - represents a single downloadable resource in a course.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class ItemStatus(str, Enum):
    """Processing status of a course item."""
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ResourceType(str, Enum):
    """Types of educational resources."""
    LECTURE_VIDEO = "Lecture Video"
    LECTURE_NOTES = "Lecture Notes"
    DPP_VIDEO = "DPP Video"
    DPP_NOTES = "DPP Notes"
    ASSIGNMENT = "Assignment"
    SOLUTION = "Solution"
    TEST = "Test"
    PYQ = "PYQ"
    HANDOUT = "Handout"
    RECORDING = "Recording"
    UNKNOWN = "Resource"


@dataclass
class CourseItem:
    """
    Complete representation of a single course resource.
    
    Attributes:
        course: Course name
        subject: Subject name
        chapter: Chapter path
        resource_type: Type of resource
        title: Item title
        url: Download URL
        index: Position in sequence
        total: Total items in sequence
    """
    
    # Required fields
    course: str
    subject: str
    chapter: str
    resource_type: str
    title: str
    url: str
    index: int
    total: int
    
    # Optional fields
    id: Optional[int] = None
    status: ItemStatus = ItemStatus.PENDING
    local_file: Optional[Path] = None
    thumbnail: Optional[Path] = None
    extension: Optional[str] = None
    downloader: Optional[str] = None
    file_size: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def formatted_index(self) -> str:
        """Format index with proper padding based on total count."""
        if self.total <= 0:
            return str(self.index)
        padding = 2 if self.total < 100 else 3
        return f"{self.index:0{padding}d}"
    
    @property
    def progress_label(self) -> str:
        """Get progress label like '07 / 42'."""
        if self.total <= 0:
            return self.formatted_index
        padding = len(str(self.total))
        return f"{self.formatted_index} / {self.total:0{padding}d}"
    
    @property
    def is_pw_video(self) -> bool:
        """Check if URL is from Physics Wallah."""
        return (
            "pw.live" in self.url.lower() or
            ("childId" in self.url and "parentId" in self.url)
        )
    
    @property
    def safe_filename(self) -> str:
        """Generate a safe filename for download."""
        safe = "".join(
            c for c in self.title[:50] 
            if c.isalnum() or c in " -_."
        ).strip()
        safe = safe.replace(" ", "_")
        return safe if safe else "unnamed"
    
    @property
    def full_path(self) -> str:
        """Get full hierarchical path of the item."""
        parts = [self.course]
        if self.subject:
            parts.append(self.subject)
        if self.chapter:
            parts.append(self.chapter)
        parts.append(self.resource_type)
        return " > ".join(parts)
    
    def mark_downloaded(
        self, 
        file_path: Path, 
        extension: str, 
        downloader: str
    ) -> None:
        """Mark item as successfully downloaded."""
        self.status = ItemStatus.DOWNLOADED
        self.local_file = file_path
        self.extension = extension
        self.downloader = downloader
        self.file_size = file_path.stat().st_size if file_path.exists() else None
        self.updated_at = datetime.now()
    
    def mark_uploaded(self) -> None:
        """Mark item as successfully uploaded."""
        self.status = ItemStatus.UPLOADED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        """Mark item as failed with error message."""
        self.status = ItemStatus.FAILED
        self.error_message = error
        self.retry_count += 1
        self.updated_at = datetime.now()
    
    def should_retry(self, max_retries: int = 3) -> bool:
        """Check if item should be retried."""
        return (
            self.status == ItemStatus.FAILED 
            and self.retry_count < max_retries
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "course": self.course,
            "subject": self.subject,
            "chapter": self.chapter,
            "resource_type": self.resource_type,
            "title": self.title,
            "url": self.url,
            "index": self.index,
            "total": self.total,
            "status": self.status.value,
            "local_file": str(self.local_file) if self.local_file else None,
            "thumbnail": str(self.thumbnail) if self.thumbnail else None,
            "extension": self.extension,
            "downloader": self.downloader,
            "file_size": self.file_size,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CourseItem":
        """Create CourseItem from dictionary."""
        return cls(
            id=data.get("id"),
            course=data["course"],
            subject=data.get("subject", ""),
            chapter=data.get("chapter", ""),
            resource_type=data.get("resource_type", "Resource"),
            title=data["title"],
            url=data["url"],
            index=data.get("index", 0),
            total=data.get("total", 0),
            status=ItemStatus(data.get("status", "pending")),
            local_file=Path(data["local_file"]) if data.get("local_file") else None,
            thumbnail=Path(data["thumbnail"]) if data.get("thumbnail") else None,
            extension=data.get("extension"),
            downloader=data.get("downloader"),
            file_size=data.get("file_size"),
            retry_count=data.get("retry_count", 0),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )
    
    def __str__(self) -> str:
        return f"{self.resource_type}: {self.title} ({self.formatted_index}/{self.total})"
    
    def __repr__(self) -> str:
        return (
            f"CourseItem(course='{self.course}', subject='{self.subject}', "
            f"chapter='{self.chapter}', title='{self.title}', "
            f"status='{self.status.value}')"
        )
