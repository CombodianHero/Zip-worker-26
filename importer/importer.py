"""
Main course importer that orchestrates the import process.
Handles both TXT and ZIP file imports.
"""

from pathlib import Path
from typing import List, Optional

from models.course_item import CourseItem
from importer.txt_parser import TxtParser
from importer.zip_extractor import ZipExtractor
from importer.folder_scanner import FolderScanner
from importer.resource_detector import ResourceDetector
from utils.logger import get_logger


class CourseImporter:
    """
    Orchestrates the import process for course content.
    
    Accepts TXT or ZIP files and produces a list of CourseItem objects
    ready for queue processing.
    """
    
    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.txt_parser = TxtParser()
        self.zip_extractor = ZipExtractor()
        self.folder_scanner = FolderScanner()
        self.resource_detector = ResourceDetector()
    
    async def import_course(
        self,
        file_path: Path,
        temp_dir: Path,
    ) -> List[CourseItem]:
        """
        Import a course from TXT or ZIP file.
        
        Args:
            file_path: Path to TXT or ZIP file
            temp_dir: Temporary directory for extraction
            
        Returns:
            List of CourseItem objects
            
        Raises:
            ValueError: If file format is not supported
        """
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return await self._import_from_txt(file_path)
        elif suffix == ".zip":
            return await self._import_from_zip(file_path, temp_dir)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    async def _import_from_txt(self, file_path: Path) -> List[CourseItem]:
        """
        Import course from a single TXT file.
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            List of CourseItem objects
        """
        self.logger.info(f"Importing from TXT: {file_path.name}")
        
        # Parse TXT file
        items = self.txt_parser.parse_file(file_path)
        
        # Detect resource type from filename
        resource_type = self.resource_detector.detect(file_path.stem)
        
        # Course name from filename
        course_name = file_path.stem
        
        # Create CourseItems
        course_items = []
        total = len(items)
        
        for idx, (title, url) in enumerate(items, 1):
            item = CourseItem(
                course=course_name,
                subject="",
                chapter="",
                resource_type=resource_type,
                title=title,
                url=url,
                index=idx,
                total=total,
            )
            course_items.append(item)
        
        self.logger.info(
            f"Created {len(course_items)} items from {file_path.name}"
        )
        return course_items
    
    async def _import_from_zip(
        self,
        zip_path: Path,
        temp_dir: Path,
    ) -> List[CourseItem]:
        """
        Import course from ZIP file with folder structure.
        
        Args:
            zip_path: Path to ZIP file
            temp_dir: Temporary directory for extraction
            
        Returns:
            List of CourseItem objects
        """
        self.logger.info(f"Importing from ZIP: {zip_path.name}")
        
        # Extract ZIP
        extracted_path = self.zip_extractor.extract(zip_path, temp_dir)
        
        # Course name from ZIP filename
        course_name = zip_path.stem
        
        # Process all TXT files in the structure
        course_items = []
        
        for folder_path, txt_file in self.folder_scanner.find_txt_files(extracted_path):
            # Extract subject (first folder level)
            subject = self._extract_subject(folder_path, extracted_path)
            
            # Extract chapter (remaining folder levels)
            chapter = self._extract_chapter(folder_path, extracted_path)
            
            # Detect resource type from filename
            resource_type = self.resource_detector.detect(txt_file.stem)
            
            # Parse TXT content
            items = self.txt_parser.parse_file(txt_file)
            
            # Create CourseItems
            total = len(items)
            for idx, (title, url) in enumerate(items, 1):
                item = CourseItem(
                    course=course_name,
                    subject=subject,
                    chapter=chapter,
                    resource_type=resource_type,
                    title=title,
                    url=url,
                    index=idx,
                    total=total,
                )
                course_items.append(item)
        
        # Cleanup extracted files
        self.zip_extractor.cleanup()
        
        self.logger.info(
            f"Created {len(course_items)} items from {zip_path.name}"
        )
        return course_items
    
    @staticmethod
    def _extract_subject(folder_path: Path, base_path: Path) -> str:
        """
        Extract subject from first folder level.
        
        Args:
            folder_path: Current folder path
            base_path: Base extraction path
            
        Returns:
            Subject name or empty string
        """
        try:
            relative = folder_path.relative_to(base_path)
            parts = relative.parts
            return parts[0] if parts else ""
        except ValueError:
            return ""
    
    @staticmethod
    def _extract_chapter(folder_path: Path, base_path: Path) -> str:
        """
        Extract chapter path from remaining folder levels.
        
        Args:
            folder_path: Current folder path
            base_path: Base extraction path
            
        Returns:
            Chapter path (folders joined with ' > ')
        """
        try:
            relative = folder_path.relative_to(base_path)
            parts = list(relative.parts)
            # Remove first part (subject)
            if len(parts) > 1:
                return " > ".join(parts[1:])
        except ValueError:
            pass
        return ""
