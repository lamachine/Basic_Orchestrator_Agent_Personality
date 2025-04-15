import asyncio
import re
import os
import sys
import traceback # Added for better error logging
from pathlib import Path # Added for better path handling

# Add src directory to Python path properly
src_dir = str(Path(__file__).parent.parent.parent.parent) # Updated path calculation
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from typing import Set, Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import datetime
from dotenv import load_dotenv


# Force reload of .env file
load_dotenv(override=True)

# Update imports to use correct paths relative to src
from src.tools.crawler.common.storage import store_chunks, supabase # Added supabase import
from src.tools.crawler.common.text_processing import ProcessedChunk, chunk_text, summarize_text # Added summarize_text
from src.tools.crawler.common.llm_provider import LLMProvider
from src.tools.crawler.common.process_chunk import process_chunk, get_embeddings

class GenericCrawler:
    def __init__(self, 
                 start_url: str, 
                 max_pages: int = 100,
                 # min_content_length is not directly used in crawl logic now, consider removing or integrating
                 # min_content_length: int = 100, 
                 chunk_size: int = 5000, # chunk_size used in common.text_processing.chunk_text
                 max_retries: int = 3,
                 delay_between_requests: float = 0.5):
        """
        Initializes the GenericCrawler.

        Args:
            start_url (str): The starting URL for the crawl.
            max_pages (int): Maximum number of pages to crawl. Defaults to 100.
            chunk_size (int): Target size for text chunks. Defaults to 5000.
            max_retries (int): Maximum number of retries for a failed URL. Defaults to 3.
            delay_between_requests (float): Delay in seconds between requests. Defaults to 0.5.
        """
        self.start_url = start_url
        self.max_pages = max_pages
        self.chunk_size = chunk_size # Stored but primarily used via common.chunk_text
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.visited_urls: Set[str] = set()
        self.failed_urls: Dict[str, str] = {}  # URL -> error message
        self.base_domain = urlparse(start_url).netloc
        
        # Configure Crawl4AI
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True
        )
        
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain we're crawling"""
        return urlparse(url).netloc == self.base_domain
        
    def normalize_url(self, url: str, base_url: str) -> str:
        """
        Normalize URL to absolute form, removing fragments and query parameters.

        Args:
            url (str): The URL to normalize.
            base_url (str): The base URL to resolve relative paths against.

        Returns:
            str: The normalized absolute URL.
        """
        # Remove fragments and query parameters
        url = url.split('#')[0].split('?')[0]
        # Convert to absolute URL
        normalized = urljoin(base_url, url)
        # Remove trailing slashes for consistency
        return normalized.rstrip('/')
        
    def clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove empty lines
        content = '\n'.join(
            line.strip() for line in content.split('\n') 
            if line.strip()
        )
        return content.strip()
        
    async def extract_links(self, html_content: str, current_url: str) -> Set[str]:
        """Extract and normalize all links from a page"""
        links = set()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Skip non-http links and anchors
            if href.startswith(('http://', 'https://', '/')):
                try:
                    normalized_url = self.normalize_url(href, current_url)
                    links.add(normalized_url)
                except Exception:
                    continue
                
        return links
        
    async def process_page(self, url: str, content: str) -> Dict[str, Any]:
        """
        Process a single page to extract title, clean text content, and generate summary.

        Args:
            url (str): The URL of the page.
            content (str): The HTML content of the page.

        Returns:
            Dict[str, Any]: A dictionary containing the URL, title, content and summary.
        """
        soup = BeautifulSoup(content, 'html.parser')
        
        # Get title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
        else:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.text.strip()
        
        # Get content (entire page)
        clean_text = self.clean_content(soup.get_text())
        
        # Generate summary using LLM
        summary = await summarize_text(clean_text[:1000])  # Summarize first 1000 chars for efficiency
        
        # Structure the page data
        page_data = {
            "url": url,
            "title": title or "Untitled Page",  # Ensure title is never null
            "content": clean_text,
            "summary": summary
        }
        
        return page_data
        
    async def crawl(self) -> Dict[str, Any]:
        """
        Main crawling logic using Crawl4AI.

        Returns:
            Dict[str, Any]: A dictionary containing crawl results and statistics.
        """
        results = {}
        
        # Note: Crawl4AI handles its own browser session management
        crawler = AsyncWebCrawler(config=self.browser_config) 
            
        urls_to_visit = {self.start_url}
            
        while urls_to_visit and len(self.visited_urls) < self.max_pages:
            current_url = urls_to_visit.pop()
            
            if current_url in self.visited_urls:
                continue
                
            print(f"Crawling: {current_url}")
            
            # Implement retry logic
            page_processed = False # Flag to check if processing was successful
            for attempt in range(self.max_retries):
                try:
                    # Configure the crawler run
                    run_config = CrawlerRunConfig(
                        # Consider CACHE_FIRST if appropriate for your use case
                        cache_mode=CacheMode.BYPASS, 
                        word_count_threshold=1, # Low threshold to get content
                        page_timeout=30000,  # 30 second timeout
                        # Use extraction strategy if needed, e.g., for specific elements
                        # extraction_strategy=JsonCssExtractionStrategy(...) 
                    )
                    
                    # Crawl the page using Crawl4AI
                    result = await crawler.arun(current_url, config=run_config)
                    
                    if result.success and result.markdown: # Check if markdown content exists
                        # Process the page content (extract title, clean text)
                        page_data = await self.process_page(current_url, result.markdown)
                        results[current_url] = page_data
                        
                        # Extract new links from the *original* HTML if available, 
                        # or fallback to markdown if necessary. Using markdown might miss some links.
                        # Prefer result.html if Crawl4AI provides it robustly. Assuming markdown for now.
                        new_links = await self.extract_links(result.markdown, current_url)
                        urls_to_visit.update(
                            url for url in new_links 
                            if url not in self.visited_urls 
                            and self.is_same_domain(url)
                        )
                        
                        page_processed = True # Mark as processed
                        # Success - break retry loop
                        break # Exit retry loop on success
                    elif not result.success:
                         raise Exception(f"Crawl4AI failed: {result.error_message or 'Unknown error'}")
                    else:
                         # Handle case where result succeeded but markdown is empty/None
                         raise Exception("Crawl4AI succeeded but returned no content.")

                except Exception as e:
                    print(f"Attempt {attempt + 1}/{self.max_retries} failed for {current_url}: {e}")
                    if attempt == self.max_retries - 1:  # Last attempt
                        print(f"Error crawling {current_url} after {self.max_retries} attempts: {e}")
                        self.failed_urls[current_url] = str(e)
                    # Exponential backoff might be better here
                    await asyncio.sleep(self.delay_between_requests * (attempt + 1)) 
                    # No 'continue' here, let the loop proceed to the next attempt or finish

            # Add to visited only if attempted (successful or failed after retries)        
            self.visited_urls.add(current_url) 
            # Add delay even after failures to avoid overwhelming the server
            await asyncio.sleep(self.delay_between_requests) 
            
        # It's good practice to explicitly close resources if Crawl4AI requires it.
        # Assuming AsyncWebCrawler handles cleanup in its context manager or destructor.
        # await crawler.close() # Uncomment if Crawl4AI has an explicit close method

        return {
            "results": results,
            "stats": {
                "total_pages_crawled": len(self.visited_urls),
                "successful_pages": len(results),
                "failed_pages": len(self.failed_urls),
                "failed_urls": self.failed_urls
            }
        }

# --- Database Functions (similar to github_crawler.py) ---

async def clear_database(source_name: str):
    """
    Clear existing entries for a specific source from the database.

    Args:
        source_name (str): The name of the source to clear.
    """
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "web_content") # Default table
        print(f"Attempting to clear entries for source '{source_name}' in table '{table_name}'...")
        # Ensure source_name is not empty or None before querying
        if not source_name:
            print("Error: source_name is empty, cannot clear database.")
            return
            
        # Delete all entries where metadata->>source equals our source_name
        # Use rpc for safety or ensure proper RLS policies are in place.
        # This direct delete assumes appropriate permissions.
        result = await supabase.from_(table_name).delete().eq('metadata->>source', source_name).execute()
        
        # Check result (supabase-py v2 syntax might differ slightly)
        # Assuming result.data might be empty on success or contain deleted count depending on version/settings
        print(f"Database clear operation for source '{source_name}' completed.") # Log regardless of count
        # if hasattr(result, 'count') and result.count is not None:
        #    print(f"Cleared {result.count} existing entries for source: {source_name}")
        # else:
        #    print(f"Cleared existing entries for source: {source_name} (count not available)")

    except Exception as e:
        print(f"Error clearing database for source '{source_name}': {e}")
        print(traceback.format_exc())


async def check_source_exists(source_name: str) -> bool:
    """
    Check if source already exists in database.

    Args:
        source_name (str): The name of the source to check.

    Returns:
        bool: True if the source exists, False otherwise.
    """
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "web_content") # Default table
        print(f"Checking if source '{source_name}' exists in table '{table_name}'...")
         # Ensure source_name is not empty or None before querying
        if not source_name:
            print("Error: source_name is empty, cannot check existence.")
            return False

        # Select 'id' or a minimal field, limit to 1
        result = await supabase.from_(table_name).select('id', count='exact').eq('metadata->>source', source_name).limit(1).execute()
        
        exists = result.count > 0
        print(f"Source '{source_name}' exists: {exists}")
        return exists
        
    except Exception as e:
        print(f"Error checking source '{source_name}': {e}")
        print(traceback.format_exc())
        return False # Assume not exists on error

# --- Main Execution Logic ---

async def main():
    """Main entry point for the generic crawler."""
    llm_provider = None # Initialize to None for finally block
    try:
        # --- Configuration Loading ---
        start_url = os.getenv("CURRENT_SOURCE")
        source_name = os.getenv("CURRENT_SOURCE_NAME") 
        source_owner = os.getenv("CURRENT_SOURCE_OWNER") 
        max_pages = int(os.getenv("MAX_PAGES", "50"))
        chunk_size = int(os.getenv("CHUNK_SIZE", "5000"))
        max_retries = int(os.getenv("MAX_RETRIES", "2"))
        delay_between_requests = float(os.getenv("DELAY_BETWEEN_REQUESTS", "0.5"))
        clear_existing = os.getenv("CLEAR_EXISTING_SOURCE", "false").lower() == "true"
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "full_site_pages") # Updated default table

        # --- Input Validation ---
        if not start_url:
            print("Error: CURRENT_SOURCE (start URL) not set in .env file")
            return
        if not source_name:
            print("Error: CURRENT_SOURCE_NAME not set in .env file")
            return
        # Optional: validate source_owner if needed

        print(f"\nStarting crawl of {start_url} for source '{source_name}'")
        print(f"Configuration:")
        print(f"- Max pages: {max_pages}")
        print(f"- Chunk size: {chunk_size}")
        print(f"- Max retries: {max_retries}")
        print(f"- Delay between requests: {delay_between_requests}s")
        print(f"- Target Table: {table_name}")
        print(f"- Clear existing data: {clear_existing}\n")

        # --- Database Check and Clear ---
        if await check_source_exists(source_name):
            print(f"Source '{source_name}' already exists in table '{table_name}'.")
            if clear_existing:
                print(f"CLEAR_EXISTING_SOURCE is true. Clearing data...")
                await clear_database(source_name)
            else:
                print("CLEAR_EXISTING_SOURCE is false. Skipping crawl for existing source.")
                # Optionally, exit or just proceed to add/update content
                # return # Uncomment to stop if source exists and clear is false
        else:
             print(f"Source '{source_name}' does not exist in table '{table_name}'. Proceeding with crawl.")


        # --- Initialization ---
        llm_provider = LLMProvider()
        crawler = GenericCrawler(
            start_url=start_url,
            max_pages=max_pages,
            chunk_size=chunk_size, # Pass chunk_size
            max_retries=max_retries,
            delay_between_requests=delay_between_requests
        )

        # --- Crawling ---
        print("Starting crawler...")
        crawl_results = await crawler.crawl()
        print("Crawler finished.")

        # --- Processing and Storing Results ---
        print(f"\nProcessing {len(crawl_results['results'])} successfully crawled pages...")
        all_processed_chunks: List[ProcessedChunk] = [] # Collect all chunks first

        for url, page_data in crawl_results['results'].items():
            print(f"- Processing: {url} (Title: {page_data.get('title', 'N/A')})")
            page_content = page_data.get("content", "")
            
            if not page_content:
                print(f"  Skipping {url} due to empty content.")
                continue

            # Create base metadata
            base_metadata = {
                "source": source_name,
                "owner": source_owner or "unknown",
                "domain": urlparse(url).netloc,
                "crawled_at": datetime.now().isoformat(),
                "content_type": "webpage"
            }

            # Split content into chunks
            raw_chunks = chunk_text(page_content, chunk_size=chunk_size) 
            print(f"  Created {len(raw_chunks)} raw chunks.")

            # Process each chunk
            for chunk_index, chunk_text in enumerate(raw_chunks):
                try:
                    # Get embeddings
                    embeddings = await get_embeddings(chunk_text)
                    
                    # Create chunk summary
                    chunk_summary = await summarize_text(chunk_text[:1000])  # Summarize first 1000 chars
                    
                    # Create processed chunk matching schema
                    processed_chunk = {
                        "url": url,
                        "chunk_number": chunk_index,
                        "title": page_data["title"],
                        "summary": chunk_summary,
                        "content": chunk_text,
                        "metadata": {
                            **base_metadata,
                            "chunk_index": chunk_index,
                            "total_chunks": len(raw_chunks)
                        },
                        "embedding": embeddings.get("nomic")  # Only use Nomic embedding
                    }
                    
                    all_processed_chunks.append(processed_chunk)
                    print(f"  Successfully processed chunk {chunk_index + 1}/{len(raw_chunks)} for {url}")
                    
                except Exception as e:
                    print(f"  Error processing chunk {chunk_index} for {url}: {e}")
                    print(traceback.format_exc())
                    continue

        # --- Storing All Chunks ---
        if all_processed_chunks:
            print(f"\nAttempting to store {len(all_processed_chunks)} processed chunks in table '{table_name}'...")
            try:
                # Store chunks in batches to avoid overwhelming the database
                batch_size = 50
                for i in range(0, len(all_processed_chunks), batch_size):
                    batch = all_processed_chunks[i:i + batch_size]
                    await store_chunks(batch, table_name=table_name)
                    print(f"Stored batch {i//batch_size + 1}/{(len(all_processed_chunks) + batch_size - 1)//batch_size}")
                print(f"Successfully stored all {len(all_processed_chunks)} chunks.")
            except Exception as e:
                print(f"Error storing chunks: {e}")
                print(traceback.format_exc())
        else:
            print("\nNo chunks were processed successfully to store.")

        # --- Print Summary ---
        print(f"\nCrawl Summary for Source '{source_name}':")
        stats = crawl_results['stats']
        print(f"Total pages attempted: {stats['total_pages_crawled']}")
        print(f"Successful pages processed: {stats['successful_pages']}")
        print(f"Failed pages: {stats['failed_pages']}")
        
        if stats['failed_pages'] > 0:
            print("\nFailed URLs:")
            for url, error in stats['failed_urls'].items():
                print(f"- {url}: {error}")
                
    except Exception as e:
        print(f"\nAn unexpected error occurred in main: {e}")
        print(traceback.format_exc())

    finally:
        # --- Cleanup ---
        if llm_provider:
            print("Closing LLM provider connection...")
            await llm_provider.close()
        print("Script finished.")


if __name__ == "__main__":
    # Consider adding argument parsing here if needed (e.g., using argparse)
    asyncio.run(main()) 