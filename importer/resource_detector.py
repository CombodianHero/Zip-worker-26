"""
Resource type detector based on TXT filenames.
Maps filenames to resource types for automatic categorization.
"""

from typing import Optional
import re


class ResourceDetector:
    """
    Detects resource types from TXT filenames.
    
    Resource types are determined by filename patterns:
    - videos.txt → Lecture Video
    - notes.txt → Lecture Notes
    - DppVideos.txt → DPP Video
    - DppNotes.txt → DPP Notes
    - And more...
    """
    
    # Resource type mappings (case-insensitive, ignores separators)
    MAPPINGS = {
        "videos": "Lecture Video",
        "lectures": "Lecture Video",
        "video": "Lecture Video",
        "notes": "Lecture Notes",
        "note": "Lecture Notes",
        "dppvideos": "DPP Video",
        "dppvideo": "DPP Video",
        "dppnotes": "DPP Notes",
        "dppnote": "DPP Notes",
        "dpp": "DPP",
        "assignment": "Assignment",
        "assignments": "Assignment",
        "solutions": "Solution",
        "solution": "Solution",
        "tests": "Test",
        "test": "Test",
        "pyq": "PYQ",
        "pyqs": "PYQ",
        "handout": "Handout",
        "handouts": "Handout",
        "slides": "Slide",
        "slide": "Slide",
        "recordings": "Recording",
        "recording": "Recording",
        "exercise": "Exercise",
        "exercises": "Exercise",
        "practice": "Practice",
        "practiceset": "Practice Set",
        "quiz": "Quiz",
        "quizzes": "Quiz",
        "revision": "Revision",
        "summary": "Summary",
        "formula": "Formula Sheet",
        "formulas": "Formula Sheet",
        "mindmap": "Mind Map",
        "ebook": "E-Book",
        "book": "E-Book",
    }
    
    @classmethod
    def detect(cls, filename: str) -> str:
        """
        Detect resource type from filename.
        
        Args:
            filename: TXT filename (with or without extension)
            
        Returns:
            Detected resource type or 'Resource' if unknown
            
        Examples:
            >>> ResourceDetector.detect("videos.txt")
            'Lecture Video'
            >>> ResourceDetector.detect("DppVideos")
            'DPP Video'
            >>> ResourceDetector.detect("notes_2024")
            'Lecture Notes'
        """
        # Remove extension
        clean = filename.rsplit(".", 1)[0] if "." in filename else filename
        
        # Normalize: lowercase, remove all non-alphanumeric
        normalized = "".join(c.lower() for c in clean if c.isalnum())
        
        # Check mappings
        for key, value in cls.MAPPINGS.items():
            if normalized == key or key in normalized:
                return value
        
        # Try partial matches
        for key, value in cls.MAPPINGS.items():
            if normalized.startswith(key) or normalized.endswith(key):
                return value
        
        # Check for keywords
        if any(kw in normalized for kw in ["video", "lecture", "class"]):
            return "Lecture Video"
        
        if any(kw in normalized for kw in ["note", "pdf", "doc", "text"]):
            return "Lecture Notes"
        
        return "Resource"
    
    @classmethod
    def get_emoji(cls, resource_type: str) -> str:
        """
        Get appropriate emoji for resource type.
        
        Args:
            resource_type: Resource type string
            
        Returns:
            Emoji character
        """
        emoji_map = {
            "Lecture Video": "🎬",
            "Lecture Notes": "📄",
            "DPP Video": "🎬",
            "DPP Notes": "📄",
            "DPP": "📝",
            "Assignment": "📝",
            "Solution": "✅",
            "Test": "📋",
            "PYQ": "📜",
            "Handout": "📑",
            "Slide": "📊",
            "Recording": "🎙️",
            "Exercise": "✏️",
            "Practice": "📝",
            "Practice Set": "📝",
            "Quiz": "❓",
            "Revision": "🔄",
            "Summary": "📋",
            "Formula Sheet": "📐",
            "Mind Map": "🧠",
            "E-Book": "📚",
        }
        
        return emoji_map.get(resource_type, "📦")
