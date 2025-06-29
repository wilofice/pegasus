"""Audio file storage service."""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
import aiofiles
from fastapi import UploadFile

from core.config import settings


class AudioStorageService:
    """Service for managing audio file storage."""
    
    def __init__(self):
        self.storage_path = Path(settings.audio_storage_path)
        self.storage_path.mkdir(exist_ok=True)
    
    def _generate_unique_filename(self, original_filename: str) -> tuple[str, str]:
        """Generate a unique filename with timestamp and random ID.
        
        Returns:
            tuple: (filename, file_path)
        """
        # Extract extension
        extension = Path(original_filename).suffix.lower()
        if not extension:
            extension = ".m4a"  # Default extension
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        filename = f"audio_{timestamp}_{random_id}{extension}"
        
        # Create directory structure (year/month/day)
        date_path = datetime.now().strftime("%Y/%m/%d")
        dir_path = self.storage_path / date_path
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = dir_path / filename
        
        return filename, str(file_path)
    
    async def save_audio_file(self, file: UploadFile, user_id: Optional[str] = None) -> dict:
        """Save uploaded audio file to storage.
        
        Args:
            file: Uploaded file from FastAPI
            user_id: Optional user ID for organization
            
        Returns:
            dict: File information including path and metadata
        """
        # Validate file size
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        # Read file to check size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.max_upload_size_bytes:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum "
                f"allowed size ({settings.max_file_size_mb}MB)"
            )
        
        # Reset file position
        await file.seek(0)
        
        # Generate filename and path
        filename, file_path = self._generate_unique_filename(file.filename or "unknown.m4a")
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size_bytes": file_size,
            "mime_type": file.content_type
        }
    
    def get_file_path(self, filename: str, date_path: Optional[str] = None) -> Optional[Path]:
        """Get full path for a file.
        
        Args:
            filename: The filename to find
            date_path: Optional date path (YYYY/MM/DD)
            
        Returns:
            Path object if file exists, None otherwise
        """
        if date_path:
            file_path = self.storage_path / date_path / filename
        else:
            # Search for file in all subdirectories
            for file_path in self.storage_path.rglob(filename):
                if file_path.is_file():
                    return file_path
            return None
        
        return file_path if file_path.exists() else None
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                
                # Try to remove empty directories
                parent = path.parent
                while parent != self.storage_path:
                    try:
                        parent.rmdir()  # Only removes if empty
                        parent = parent.parent
                    except OSError:
                        break
                
                return True
            return False
        except Exception:
            return False
    
    def get_file_stats(self, file_path: str) -> Optional[dict]:
        """Get file statistics.
        
        Args:
            file_path: Full path to the file
            
        Returns:
            dict: File statistics or None if not found
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                stats = path.stat()
                return {
                    "size_bytes": stats.st_size,
                    "created_at": datetime.fromtimestamp(stats.st_ctime),
                    "modified_at": datetime.fromtimestamp(stats.st_mtime),
                    "exists": True
                }
            return None
        except Exception:
            return None