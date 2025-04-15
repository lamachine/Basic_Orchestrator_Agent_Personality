import os
import sys
import traceback
from pathlib import Path

# Add src directory to Python path properly
src_dir = str(Path(__file__).parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import asyncio
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any
from datetime import datetime

# Update imports to use correct paths
from src.tools.crawler.common.text_processing import chunk_text, RawContent, ProcessedChunk
from src.tools.crawler.common.storage import store_chunks, supabase
from src.tools.crawler.common.llm_provider import LLMProvider
from src.tools.crawler.common.process_chunk import process_chunk, get_title_and_summary

# Force reload of .env file
load_dotenv(override=True)

# Initialize clients
llm_provider = LLMProvider()

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable not set")

# Set default repo URL to Cursor docs if not specified
REPO_URL = os.getenv('CURRENT_SOURCE_BASE_URL')
if not REPO_URL:
    raise ValueError("CURRENT_SOURCE_BASE_URL environment variable not set")
print(f"Using repository: {REPO_URL}")

# Initialize HTTP client
client = httpx.AsyncClient()
headers = {"Authorization": f"token {GITHUB_TOKEN}"}

async def get_repo_structure(repo_url: str) -> List[str]:
    """Get the repository structure."""
    # Extract owner and repo from URL
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]

    # Try main branch first, then master
    for branch in ['main', 'master']:
        try:
            # Set up GitHub API request
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            print(f"Fetching repo structure from: {api_url}")
            
            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("truncated", False):
                print("Warning: Repository tree was truncated due to size!")

            # Extract file paths
            files = [item["path"] for item in data["tree"] if item["type"] == "blob"]
            print(f"Found {len(files)} files in repository")
            return files

        except Exception as e:
            if branch == 'master':  # Only print error if both branches fail
                print(f"Error getting repo structure: {e}")
                if isinstance(e, httpx.HTTPStatusError):
                    print(f"HTTP Status: {e.response.status_code}")
                    print(f"Response: {e.response.text}")
    
    return []

async def get_file_content(repo_url: str, file_path: str) -> str:
    """Get the content of a file from the repository."""
    # Extract owner and repo from URL
    parts = repo_url.rstrip("/").split("/")
    owner = parts[-2]
    repo = parts[-1]

    # Try main branch first, then master
    for branch in ['main', 'master']:
        try:
            # Set up GitHub API request
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"

            response = await client.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Get raw content
            if "content" in data:
                import base64
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content
            return ""

        except Exception as e:
            if branch == 'master':  # Only print error if both branches fail
                print(f"Error getting file content: {e}")
    
    return ""

async def process_and_store_document(content: str, file_path: str, repo_url: str):
    """Process a document and store its chunks."""
    try:
        # Create metadata
        metadata = {
            "source": os.getenv("CURRENT_SOURCE_NAME"),
            "owner": os.getenv("CURRENT_SOURCE_OWNER"),
            "file_path": file_path,
            "repo_url": repo_url,
            "crawled_at": datetime.now().isoformat()
        }

        # Split into chunks
        chunks = chunk_text(content)
        print(f"\nProcessing {len(chunks)} chunks for {file_path}")
        
        # Process chunks in parallel
        tasks = [
            process_chunk(
                chunk, 
                i, 
                f"{repo_url}/blob/main/{file_path}", 
                llm_provider,
                metadata=metadata
            ) 
            for i, chunk in enumerate(chunks)
        ]
        processed_chunks = await asyncio.gather(*tasks)
        
        # Store chunks - properly awaiting the async function
        await store_chunks(processed_chunks)
        print(f"Successfully stored {len(processed_chunks)} chunks for {file_path}")
        
    except Exception as e:
        print(f"\nError processing document {file_path}:")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        print(f"Processing state:")
        print(f"- Chunks created: {len(chunks) if 'chunks' in locals() else 'Not created'}")
        print(f"- Tasks created: {len(tasks) if 'tasks' in locals() else 'Not created'}")
        print(f"- Processed chunks: {len(processed_chunks) if 'processed_chunks' in locals() else 'Not created'}")
        print("Full traceback:")
        print(traceback.format_exc())

async def clear_database(source_name: str):
    """Clear existing entries for a specific source from the database."""
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "repo_content")
        # Delete all entries where metadata->source equals our source_name
        result = supabase.from_(table_name).delete().eq('metadata->>source', source_name).execute()
        print(f"Cleared existing entries for source: {source_name}")
    except Exception as e:
        print(f"Error clearing database: {e}")

async def check_source_exists(source_name: str) -> bool:
    """Check if source already exists in database."""
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "repo_content")
        result = supabase.from_(table_name).select('id').eq('metadata->>source', source_name).limit(1).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"Error checking source: {e}")
        return False

async def download_repo(repo_url: str):
    """Download all files from a repository."""
    try:
        # Get repository structure
        print(f"Getting structure for {repo_url}...")
        files = await get_repo_structure(repo_url)
        print(f"Found {len(files)} files")
        
        # Download and process each file
        for i, file_path in enumerate(files, 1):
            print(f"\nDownloading {i}/{len(files)}: {file_path}")
            content = await get_file_content(repo_url, file_path)
            print(f"Downloaded {len(content)} characters")
            
            # Process and store the content
            await process_and_store_document(content, file_path, repo_url)
    
    except Exception as e:
        print(f"Error downloading repo: {e}")

async def main():
    """Main entry point."""
    try:
        source_name = os.getenv("CURRENT_SOURCE_NAME")
        if not source_name:
            print("Error: CURRENT_SOURCE_NAME not set in environment")
            return
            
        # Check if source exists and clear if needed
        if await check_source_exists(source_name):
            print(f"Source {source_name} exists in database")
            if os.getenv("CLEAR_EXISTING_SOURCE", "").lower() == "true":
                print(f"Clearing existing entries for {source_name}")
                await clear_database(source_name)
        
        print(f"Starting download of repository: {REPO_URL}")
        await download_repo(REPO_URL)
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.aclose()
        await llm_provider.close()

if __name__ == "__main__":
    asyncio.run(main()) 