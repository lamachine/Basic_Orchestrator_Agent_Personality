"""
Google Drive API Tools
"""

import io
import json
import logging
import os
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .credentials import CredentialsHandler, get_credentials


@lru_cache(maxsize=1)
def get_drive_service():
    """Get and cache the Google Drive service."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def list_files(max_results: int = 10, query: str = "", order_by: str = "modifiedTime desc") -> str:
    """
    List files from Google Drive.

    Args:
        max_results: Maximum number of files to return
        query: Search query (see Google Drive API docs for syntax)
        order_by: How to sort the files

    Returns:
        str: JSON string containing file list
    """
    try:
        service = get_drive_service()
        results = (
            service.files()
            .list(
                pageSize=max_results,
                q=query,
                orderBy=order_by,
                fields="files(id, name, mimeType, modifiedTime, size, parents)",
            )
            .execute()
        )

        return str(results.get("files", []))
    except Exception as e:
        return f"Error listing files: {str(e)}"


def upload_file(
    file_path: str,
    parent_folder_id: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> str:
    """
    Upload a file to Google Drive.

    Args:
        file_path: Path to the file to upload
        parent_folder_id: Optional folder ID to upload to
        mime_type: Optional MIME type of the file

    Returns:
        str: File ID of the uploaded file
    """
    try:
        service = get_drive_service()
        file_metadata = {"name": os.path.basename(file_path)}

        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        return f"File uploaded successfully. File ID: {file.get('id')}"
    except Exception as e:
        return f"Error uploading file: {str(e)}"


def download_file(file_id: str, output_path: str) -> str:
    """
    Download a file from Google Drive.

    Args:
        file_id: ID of the file to download
        output_path: Where to save the downloaded file

    Returns:
        str: Success or error message
    """
    try:
        service = get_drive_service()
        request = service.files().get_media(fileId=file_id)

        with io.FileIO(output_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        return f"File downloaded successfully to {output_path}"
    except Exception as e:
        return f"Error downloading file: {str(e)}"


def create_folder(folder_name: str, parent_folder_id: Optional[str] = None) -> str:
    """
    Create a new folder in Google Drive.

    Args:
        folder_name: Name of the folder to create
        parent_folder_id: Optional parent folder ID

    Returns:
        str: Folder ID of the created folder
    """
    try:
        service = get_drive_service()
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        file = service.files().create(body=file_metadata, fields="id").execute()

        return f"Folder created successfully. Folder ID: {file.get('id')}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"


def delete_file(file_id: str) -> str:
    """
    Delete a file from Google Drive.

    Args:
        file_id: ID of the file to delete

    Returns:
        str: Success or error message
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        return f"File {file_id} deleted successfully"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


def share_file(file_id: str, email: str, role: str = "reader") -> str:
    """
    Share a file with another user.

    Args:
        file_id: ID of the file to share
        email: Email address to share with
        role: Permission role (reader, writer, commenter, owner)

    Returns:
        str: Success or error message
    """
    try:
        service = get_drive_service()
        permission = {"type": "user", "role": role, "emailAddress": email}

        result = (
            service.permissions()
            .create(fileId=file_id, body=permission, sendNotificationEmail=True)
            .execute()
        )

        return f"File shared successfully with {email}"
    except Exception as e:
        return f"Error sharing file: {str(e)}"


def move_file(file_id: str, folder_id: str) -> str:
    """
    Move a file to a different folder.

    Args:
        file_id: ID of the file to move
        folder_id: ID of the destination folder

    Returns:
        str: Success or error message
    """
    try:
        service = get_drive_service()

        # Get current parents
        file = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))

        # Move the file
        file = (
            service.files()
            .update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields="id, parents",
            )
            .execute()
        )

        return f"File moved successfully to folder {folder_id}"
    except Exception as e:
        return f"Error moving file: {str(e)}"


def get_file_info(file_id: str) -> str:
    """
    Get detailed information about a file.

    Args:
        file_id: ID of the file

    Returns:
        str: File information
    """
    try:
        service = get_drive_service()
        file = service.files().get(fileId=file_id, fields="*").execute()

        return str(file)
    except Exception as e:
        return f"Error getting file info: {str(e)}"


# Direct testing
if __name__ == "__main__":
    print("\nTesting Google Drive API:")
    try:
        # Test listing files
        print("\n1. Testing list_files():")
        files = list_files(max_results=5)
        print(files)

        # Test creating a folder
        print("\n2. Testing create_folder():")
        folder_result = create_folder("Test Folder")
        print(folder_result)
        folder_id = folder_result.split(": ")[-1]

        # Test uploading a file
        print("\n3. Testing upload_file():")
        # Create a test file
        with open("test_file.txt", "w") as f:
            f.write("This is a test file")

        upload_result = upload_file("test_file.txt", parent_folder_id=folder_id)
        print(upload_result)
        file_id = upload_result.split(": ")[-1]

        # Test getting file info
        print("\n4. Testing get_file_info():")
        print(get_file_info(file_id))

        # Test sharing the file
        print("\n5. Testing share_file():")
        print(share_file(file_id, "test@example.com"))

        # Test moving the file
        print("\n6. Testing move_file():")
        new_folder_result = create_folder("New Test Folder")
        new_folder_id = new_folder_result.split(": ")[-1]
        print(move_file(file_id, new_folder_id))

        # Clean up
        print("\n7. Cleaning up:")
        print(delete_file(file_id))
        print(delete_file(folder_id))
        print(delete_file(new_folder_id))
        os.remove("test_file.txt")

        print("\nAll tests completed successfully!")

    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback

        print("\nFull traceback:")
        print(traceback.format_exc())
