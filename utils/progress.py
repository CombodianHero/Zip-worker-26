"""
Progress tracking utility for downloads and uploads.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Callable


@dataclass
class ProgressTracker:
    """
    Track progress of file operations with speed and ETA calculation.
    
    Features:
    - Real-time speed calculation
    - ETA estimation
    - Progress percentage
    - Progress bar generation
    """
    
    total: int = 0
    current: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    last_bytes: int = 0
    
    def update(self, current: int, total: Optional[int] = None) -> dict:
        """
        Update progress and return stats.
        
        Args:
            current: Current bytes processed
            total: Total bytes (if known)
            
        Returns:
            Dictionary with progress statistics
        """
        if total is not None:
            self.total = total
        
        self.current = current
        now = time.time()
        elapsed = now - self.last_update
        
        # Calculate speed (only update every 0.5 seconds)
        if elapsed >= 0.5:
            bytes_diff = current - self.last_bytes
            self._speed = bytes_diff / elapsed if elapsed > 0 else 0
            self.last_update = now
            self.last_bytes = current
        
        return self.get_stats()
    
    def get_stats(self) -> dict:
        """
        Get current progress statistics.
        
        Returns:
            Dictionary with progress info
        """
        elapsed = time.time() - self.start_time
        
        # Calculate percentage
        if self.total > 0:
            percentage = (self.current / self.total) * 100
        else:
            percentage = 0
        
        # Calculate speed
        if elapsed > 0:
            avg_speed = self.current / elapsed
        else:
            avg_speed = 0
        
        # Calculate ETA
        if self.total > 0 and avg_speed > 0:
            remaining = self.total - self.current
            eta = remaining / avg_speed
        else:
            eta = None
        
        return {
            "current": self.current,
            "total": self.total,
            "percentage": percentage,
            "speed": getattr(self, "_speed", avg_speed),
            "avg_speed": avg_speed,
            "eta": eta,
            "elapsed": elapsed,
            "progress_bar": self._generate_bar(percentage),
        }
    
    def _generate_bar(self, percentage: float, width: int = 20) -> str:
        """
        Generate a text progress bar.
        
        Args:
            percentage: Completion percentage
            width: Bar width in characters
            
        Returns:
            Progress bar string (e.g., '[████████░░░░░░░░] 50%')
        """
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percentage:.1f}%"
    
    def reset(self) -> None:
        """Reset the tracker."""
        self.current = 0
        self.total = 0
        self.start_time = time.time()
        self.last_update = time.time()
        self.last_bytes = 0


def create_progress_callback(
    tracker: ProgressTracker,
    status_callback: Optional[Callable] = None,
) -> Callable:
    """
    Create a progress callback function.
    
    Args:
        tracker: ProgressTracker instance
        status_callback: Optional callback for status updates
        
    Returns:
        Progress callback function
    """
    async def callback(current: int, total: int, speed: float, eta: Optional[float]) -> None:
        """Progress callback for downloads/uploads."""
        stats = tracker.update(current, total)
        
        if status_callback:
            await status_callback(stats)
    
    return callback
