"""File Storage Service - Manages file storage and retrieval for artifacts."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class FileStorageService:
    """Service for storing and retrieving generated files."""
    
    def __init__(self, base_path: str = "/tmp/synzept-artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, 
                  user_id: UUID,
                  file_path: str,
                  artifact_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Save a file and create metadata record.
        
        Args:
            user_id: User ID
            file_path: Path to the file to save
            artifact_metadata: Metadata about the artifact
            
        Returns:
            File record dict with storage info, or None if failed
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            # Create user directory
            user_dir = self.base_path / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Get file info
            file_name = Path(file_path).name
            file_size = os.path.getsize(file_path)
            
            # Create storage record
            file_record = {
                "id": artifact_metadata.get("id"),
                "user_id": str(user_id),
                "filename": file_name,
                "file_path": file_path,
                "storage_path": str(user_dir / file_name),
                "file_size": file_size,
                "file_type": artifact_metadata.get("file_type", "application/pdf"),
                "title": artifact_metadata.get("title"),
                "description": artifact_metadata.get("description"),
                "created_at": datetime.utcnow().isoformat(),
                "action_id": artifact_metadata.get("action_id"),
                "task_id": artifact_metadata.get("task_id"),
                "metadata": artifact_metadata,
            }
            
            return file_record
        
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    def get_file_path(self, user_id: UUID, artifact_id: str) -> Optional[str]:
        """Get the storage path for a file."""
        user_dir = self.base_path / str(user_id)
        if user_dir.exists():
            # Look for file with artifact_id in metadata
            for file_path in user_dir.glob("**/*"):
                if file_path.is_file():
                    return str(file_path)
        return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    def get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        if self.file_exists(file_path):
            return os.path.getsize(file_path)
        return 0
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        try:
            if self.file_exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
