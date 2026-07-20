"""
QueueItem model for managing the processing queue.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from models.course_item import CourseItem


class QueueStatus(str, Enum):
    """Status of a queue item."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    """
    Represents an item in the processing queue.
    
    Wraps a CourseItem with queue-specific metadata like
    priority, status tracking, and retry counts.
    """
    
    item: CourseItem
    status: QueueStatus = QueueStatus.PENDING
    priority: int = 0
    added_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    
    def start(self) -> None:
        """Mark item as started processing."""
        self.status = QueueStatus.DOWNLOADING
        self.started_at = datetime.now()
        self.item.status = "downloading"
    
    def complete(self) -> None:
        """Mark item as completed."""
        self.status = QueueStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def fail(self) -> None:
        """Mark item as failed."""
        self.status = QueueStatus.FAILED
        self.retry_count += 1
        self.completed_at = datetime.now()
    
    def pause(self) -> None:
        """Pause processing."""
        self.status = QueueStatus.PAUSED
    
    def cancel(self) -> None:
        """Cancel processing."""
        self.status = QueueStatus.CANCELLED
        self.completed_at = datetime.now()
    
    @property
    def is_active(self) -> bool:
        """Check if item is currently being processed."""
        return self.status in [QueueStatus.DOWNLOADING, QueueStatus.UPLOADING]
    
    @property
    def is_finished(self) -> bool:
        """Check if item processing is finished."""
        return self.status in [
            QueueStatus.COMPLETED,
            QueueStatus.FAILED,
            QueueStatus.CANCELLED,
        ]
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed processing time in seconds."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return (end_time - self.started_at).total_seconds()
        return None
    
    def __lt__(self, other: "QueueItem") -> bool:
        """Compare by priority (lower = higher priority)."""
        return self.priority < other.priority
