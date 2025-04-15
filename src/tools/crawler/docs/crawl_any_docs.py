import os
import sys
# Add src directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import json
import asyncio
import requests
from xml.etree import ElementTree
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import httpx

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawler.common.llm_provider import LLMProvider
from crawler.common.text_processing import chunk_text, RawContent, ProcessedChunk
from crawler.common.storage import store_chunks, supabase
from src.tools.crawler.common.process_chunk import process_chunk, get_title_and_summary

# Force reload of .env file
load_dotenv(override=True)

# Initialize clients
llm_provider = LLMProvider()

# Configure browser with viewport settings
browser_config = BrowserConfig(
    headless=True,
    ignore_https_errors=True,
    extra_args=['--disable-gpu', '--no-sandbox']
)

# Debug prints
print("\nEnvironment variables loaded:")
print(f"CURRENT_SOURCE_NAME: {os.getenv('CURRENT_SOURCE_NAME')}")
print(f"CURRENT_SOURCE_BASE_URL: {os.getenv('CURRENT_SOURCE_BASE_URL')}")
print(f"CURRENT_SOURCE_SITEMAP_URL: {os.getenv('CURRENT_SOURCE_SITEMAP_URL')}\n")

@dataclass
class CrawlSource:
    name: str
    base_url: str
    sitemap_url: Optional[str] = None
    url_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None

async def get_urls_from_sitemap(sitemap_url: str) -> Set[str]:
    """Extract URLs from a sitemap XML."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(sitemap_url)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            
            # Extract URLs from sitemap
            urls = set()
            for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
                urls.add(url.text)
                
            return urls
    except Exception as e:
        print(f"Error parsing sitemap {sitemap_url}: {e}")
        return set()

async def process_and_store_document(url: str, markdown: str, llm_provider: LLMProvider):
    """Process a document and store its chunks."""
    try:
        # Split into chunks
        chunks = chunk_text(markdown)
        print(f"\nProcessing {len(chunks)} chunks for {url}")
        
        # Process chunks in parallel
        tasks = [
            process_chunk(chunk, i, url, llm_provider) 
            for i, chunk in enumerate(chunks)
        ]
        processed_chunks = await asyncio.gather(*tasks)
        
        # Store chunks
        store_chunks(processed_chunks)
        
    except Exception as e:
        print(f"Error processing document {url}: {e}")

async def get_urls_from_robots(base_url: str) -> List[str]:
    """Get URLs from robots.txt."""
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(robots_url)
            response.raise_for_status()
            
            if response.url != robots_url:
                print(f"Followed redirect from {robots_url} to {response.url}")
            
            urls = set()
            for line in response.text.split('\n'):
                if line.startswith('Allow:') or line.startswith('Disallow:'):
                    path = line.split(': ')[1].strip()
                    if path and not path == '/':
                        url = urljoin(base_url, path)
                        urls.add(url)
            return list(urls)
    except Exception as e:
        print(f"Error fetching robots.txt: {e}")
        if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 301:
            print(f"Redirect location: '{e.response.headers.get('location')}'")
        return []

async def get_urls_from_feed(base_url: str) -> List[str]:
    """Get URLs from RSS/Atom feeds."""
    feed_paths = ['/feed', '/rss', '/atom.xml', '/feed.xml', '/rss.xml']
    urls = set()
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for path in feed_paths:
            try:
                feed_url = urljoin(base_url, path)
                response = await client.get(feed_url)
                response.raise_for_status()
                
                if response.url != feed_url:
                    print(f"Followed redirect from {feed_url} to {response.url}")
                
                # Try to parse as XML and extract links
                try:
                    root = ElementTree.fromstring(response.content)
                    # Add feed-specific URL extraction here if needed
                    urls.update(extract_urls_from_feed(root))
                except ElementTree.ParseError:
                    continue
                    
            except Exception as e:
                continue
                
    return list(urls)

async def get_urls_from_html_discovery(base_url: str, url_patterns: Optional[List[str]] = None) -> Set[str]:
    """Discover URLs by crawling HTML pages, with special handling for SPAs."""
    discovered_urls = set()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            # Configure browser for SPA crawling
            browser_config = BrowserConfig(
                headless=True,
                ignore_https_errors=True,
                extra_args=['--disable-gpu', '--no-sandbox']
            )
            
            # Configure crawler for SPAs
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_for_selector=os.getenv('WAIT_FOR_SELECTOR', 'main'),
                wait_for_timeout=int(os.getenv('JS_RENDER_TIMEOUT', '5000')),
                scroll_for_dynamic=os.getenv('SCROLL_FOR_DYNAMIC', 'true').lower() == 'true'
            )

            async with AsyncWebCrawler(browser_config) as crawler:
                # Start with base URL
                urls_to_check = {base_url}
                
                while urls_to_check:
                    current_url = urls_to_check.pop()
                    if not should_process_url(current_url, base_url, url_patterns):
                        continue

                    print(f"\nChecking URL: {current_url}")
                    try:
                        # Get page content with JavaScript rendering
                        response = await crawler.get_page_content(current_url, config=crawl_config)
                        
                        # Extract links from rendered content
                        soup = BeautifulSoup(response, 'html.parser')
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            full_url = urljoin(current_url, href)
                            
                            if should_process_url(full_url, base_url, url_patterns):
                                urls_to_check.add(full_url)
                                discovered_urls.add(full_url)
                                print(f"Found URL: {full_url}")
                    
                    except Exception as e:
                        print(f"Error processing {current_url}: {str(e)}")
                        continue

        except Exception as e:
            print(f"Error during HTML discovery: {str(e)}")
    
    return discovered_urls

def should_process_url(url: str, base_url: str, url_patterns: Optional[List[str]] = None) -> bool:
    """Check if a URL should be processed based on patterns and base URL."""
    if not url.startswith(base_url):
        return False
        
    if not url_patterns:
        return True
        
    return any(pattern in url for pattern in url_patterns)

async def get_urls_for_source(source: CrawlSource) -> List[str]:
    """Get URLs based on source configuration using multiple discovery methods."""
    urls = set()
    
    print(f"\nDiscovering URLs for {source.name}:")
    
    # Try sitemap if provided
    if source.sitemap_url:
        sitemap_urls = await get_urls_from_sitemap(source.sitemap_url)
        print(f"- Found {len(sitemap_urls)} URLs from sitemap")
        urls.update(sitemap_urls)
    
    # Try robots.txt
    robots_urls = await get_urls_from_robots(source.base_url)
    print(f"- Found {len(robots_urls)} URLs from robots.txt")
    urls.update(robots_urls)
    
    # Try feeds
    feed_urls = await get_urls_from_feed(source.base_url)
    print(f"- Found {len(feed_urls)} URLs from feeds")
    urls.update(feed_urls)
    
    # Try HTML discovery
    html_urls = await get_urls_from_html_discovery(source.base_url, source.url_patterns)
    print(f"- Found {len(html_urls)} URLs from HTML discovery")
    urls.update(html_urls)
    
    # Filter URLs
    filtered_urls = list(urls)
    if source.exclude_patterns:
        filtered_urls = [
            url for url in filtered_urls 
            if not any(pattern in url for pattern in source.exclude_patterns)
        ]
    
    print(f"\nFinal results:")
    print(f"- Total unique URLs: {len(filtered_urls)}")
    print("- First few URLs:")
    for url in list(filtered_urls)[:5]:
        print(f"  * {url}")
    
    return filtered_urls

async def crawl_parallel(urls: List[str], source: CrawlSource, max_concurrent: int = 5):
    """Crawl multiple URLs in parallel with a concurrency limit."""
    # Initialize crawler with separate browser and crawler configs
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Create crawler with browser config
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        semaphore = asyncio.Semaphore(max_concurrent)
        total_urls = len(urls)
        successful = 0
        failed = 0
        
        async def process_url(url: str):
            nonlocal successful, failed
            try:
                async with semaphore:
                    result = await crawler.arun(
                        url=url,
                        config=crawl_config,
                        session_id="session1"
                    )
                    if result.success:
                        await process_and_store_document(url, result.markdown_v2.raw_markdown, llm_provider)
                        successful += 1
                        print(f"\nProgress: {successful + failed}/{total_urls} URLs processed")
                        print(f"Success: {successful}, Failed: {failed}")
                    else:
                        failed += 1
                        print(f"Failed to crawl {url}: {result.error_message}")
            except Exception as e:
                failed += 1
                print(f"Error processing {url}: {e}")
        
        await asyncio.gather(*[process_url(url) for url in urls])
        
        print(f"\nCrawl completed:")
        print(f"Total URLs: {total_urls}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
    finally:
        await crawler.close()

async def clear_database(source_name: str):
    """Clear existing entries for a specific source from the database."""
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "dev_docs_site_pages")
        # Delete all entries where metadata->source equals our source_name
        result = supabase.from_(table_name).delete().eq('metadata->>source', source_name).execute()
        print(f"Cleared existing entries for source: {source_name}")
    except Exception as e:
        print(f"Error clearing database: {e}")

async def check_source_exists(source_name: str) -> bool:
    """Check if source already exists in database."""
    try:
        table_name = os.getenv("CURRENT_SOURCE_TABLE", "dev_docs_site_pages")
        result = supabase.from_(table_name).select('id').eq('metadata->>source', source_name).limit(1).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"Error checking source: {e}")
        return False

async def get_source_config() -> CrawlSource:
    """Get source configuration from environment variables."""
    return CrawlSource(
        name=os.getenv("CURRENT_SOURCE_NAME"),
        base_url=os.getenv("CURRENT_SOURCE_BASE_URL"),
        sitemap_url=os.getenv("CURRENT_SOURCE_SITEMAP_URL") or None,
        url_patterns=[p.strip() for p in os.getenv("CURRENT_SOURCE_URL_PATTERNS", "").split(",")] if os.getenv("CURRENT_SOURCE_URL_PATTERNS") else None,
        exclude_patterns=[p.strip() for p in os.getenv("CURRENT_SOURCE_EXCLUDE_PATTERNS", "").split(",")] if os.getenv("CURRENT_SOURCE_EXCLUDE_PATTERNS") else None
    )

async def main():
    """Main entry point."""
    try:
        # Initialize LLM provider
        llm_provider = LLMProvider()
        
        # Get source configuration
        source = await get_source_config()
        if not source.name:
            print("Error: CURRENT_SOURCE_NAME not set in environment")
            return
            
        # Check if source exists and clear if needed
        if await check_source_exists(source.name):
            print(f"Source {source.name} exists in database")
            if os.getenv("CLEAR_EXISTING_SOURCE", "").lower() == "true":
                print(f"Clearing existing entries for {source.name}")
                await clear_database(source.name)
        
        # Initialize crawler with separate browser and crawler configs
        browser_config = BrowserConfig(
            headless=True,
            ignore_https_errors=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        
        # Create crawler with browser config
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()
        
        # Get URLs to crawl
        urls = await get_urls_for_source(source)
        print(f"Found {len(urls)} URLs to crawl")
        
        # Process each URL
        for url in urls:
            try:
                print(f"\nProcessing {url}")
                result = await crawler.arun(
                    url=url,
                    config=crawl_config,
                    session_id="session1"
                )
                if result.success:
                    await process_and_store_document(url, result.markdown_v2.raw_markdown, llm_provider)
                else:
                    print(f"No content found for {url}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Cleanup
        await crawler.close()
        await llm_provider.close()
        
    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 