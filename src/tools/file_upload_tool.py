"""File upload tool for the orchestrator.

Allows users to upload and process files for analysis.
"""

import os
import shutil
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .base_tool import BaseTool

# Setup logging
logger = logging.getLogger(__name__)

class FileUploadTool(BaseTool):
    """Tool for handling file uploads and making them available for analysis."""
    
    # Common text file extensions
    TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml',
        '.yaml', '.yml', '.ini', '.conf', '.sh', '.bat', '.ps1', '.log',
        '.csv', '.tsv', '.rst', '.rtf', '.tex', '.sql'
    }
    
    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize the file upload tool.
        
        Args:
            upload_dir: Optional custom upload directory path. If not provided,
                      defaults to './uploads' in the project directory.
        """
        super().__init__(
            name="file_upload",
            description="Upload and process files for analysis by the orchestrator"
        )
        
        # Set up upload directory
        self.upload_dir = upload_dir or os.path.join(os.getcwd(), 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # Initialize metadata storage
        self.metadata_file = os.path.join(self.upload_dir, 'metadata.json')
        self._init_metadata()

    def _init_metadata(self):
        """Initialize or load metadata storage."""
        if os.path.exists(self.metadata_file):
            import json
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
            self._save_metadata()

    def _save_metadata(self):
        """Save metadata to file."""
        import json
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _estimate_tokens(self, file_path: str) -> Tuple[Optional[int], str]:
        """
        Estimate the number of tokens in a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (estimated token count or None, estimation method used)
        """
        # Check if it's a text file
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.TEXT_EXTENSIONS:
            return None, "non-text file"
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple word-based estimation (avg 1.3 tokens per word)
            word_count = len(content.split())
            estimated_tokens = int(word_count * 1.3)
            
            # Character-based backup estimation (avg 4 chars per token)
            char_count = len(content)
            char_based_estimate = int(char_count / 4)
            
            # Use the larger of the two estimates to be conservative
            final_estimate = max(estimated_tokens, char_based_estimate)
            
            return final_estimate, "word/char estimation"
            
        except UnicodeDecodeError:
            return None, "non-text encoding"
        except Exception as e:
            logger.warning(f"Error estimating tokens: {e}")
            return None, f"error: {str(e)}"

    async def execute(self, file_path: str, move_file: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Execute the file upload operation.
        
        Args:
            file_path: Path to the file to upload
            move_file: Whether to move the file instead of copying (default: False)
            **kwargs: Additional parameters
            
        Returns:
            Dict containing upload results and file metadata
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            # Get file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_hash = self._calculate_file_hash(file_path)
            
            # Estimate tokens
            estimated_tokens, estimation_method = self._estimate_tokens(file_path)
            
            # Generate unique filename if needed
            target_path = os.path.join(self.upload_dir, file_name)
            if os.path.exists(target_path):
                base, ext = os.path.splitext(file_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"{base}_{timestamp}{ext}"
                target_path = os.path.join(self.upload_dir, file_name)

            # Copy or move file
            if move_file:
                shutil.move(file_path, target_path)
            else:
                shutil.copy2(file_path, target_path)

            # Store metadata
            metadata = {
                "original_name": os.path.basename(file_path),
                "stored_name": file_name,
                "size_bytes": file_size,
                "hash": file_hash,
                "upload_time": datetime.now().isoformat(),
                "mime_type": self._get_mime_type(target_path),
                "path": target_path,
                "operation": "moved" if move_file else "copied",
                "token_estimate": {
                    "count": estimated_tokens,
                    "method": estimation_method
                }
            }
            
            self.metadata[file_hash] = metadata
            self._save_metadata()

            return {
                "success": True,
                "file_hash": file_hash,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error uploading file: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type of file."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def get_file_info(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an uploaded file.
        
        Args:
            file_hash: Hash of the file to look up
            
        Returns:
            File metadata if found, None otherwise
        """
        return self.metadata.get(file_hash)

    def list_files(self) -> Dict[str, Any]:
        """
        List all uploaded files.
        
        Returns:
            Dictionary of file hashes to metadata
        """
        return self.metadata.copy()

# Create tool instance function
async def file_upload_tool(task: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Create and execute a file upload tool instance.
    
    Args:
        task: Optional task description
        **kwargs: Additional parameters
        
    Returns:
        Tool execution results
    """
    tool = FileUploadTool()
    return await tool.execute(task, **kwargs) if task else {
        "success": False,
        "error": "No file path provided"
    } 