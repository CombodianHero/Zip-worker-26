from dataclasses import dataclass
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
    
    @property
    def formatted_index(self) -> str:
        if self.total <= 0:
            return str(self.index)
        padding = 2 if self.total < 100 else 3
        return f"{self.index:0{padding}d}"
    
    @property
    def is_pw_video(self) -> bool:
        return "childId" in self.url and "parentId" in self.url
