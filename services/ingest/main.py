"""Text extraction service for Audiobook Server.

This service extracts text from PDF, EPUB, and TXT files with OCR fallback.
It follows a functional approach with clear separation of concerns.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from functools import wraps

import redis
import httpx
import pdfplumber
import ebooklib
from ebooklib import epub
import chardet
from PIL import Image
import pytesseract
from bs4 import BeautifulSoup

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type aliases for clarity
FilePath = Union[str, Path]
ExtractedText = str
BookId = str

@dataclass
class ExtractionResult:
    """Result of text extraction operation."""
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    encoding: Optional[str] = None


def with_error_handling(func: Callable) -> Callable:
    """Decorator for consistent error handling across extractors."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> ExtractionResult:
        try:
            result = func(*args, **kwargs)
            return ExtractionResult(success=True, text=result)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return ExtractionResult(success=False, error=str(e))
    return wrapper


@with_error_handling
def extract_pdf_text(file_path: FilePath) -> str:
    """Extract text from PDF using pdfplumber with OCR fallback."""
    text_parts = []
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Try text extraction first
            text = page.extract_text()
            
            if not text or text.strip() == "":
                # Fallback to OCR
                logger.info(f"Using OCR for page {page_num}")
                image = page.to_image()
                text = pytesseract.image_to_string(image.original)
            
            if text and text.strip():
                text_parts.append(text.strip())
    
    return "\n\n".join(text_parts)


@with_error_handling
def extract_epub_text(file_path: FilePath) -> str:
    """Extract text from EPUB using ebooklib."""
    book = epub.read_epub(file_path)
    text_parts = []
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()
            if text and text.strip():
                text_parts.append(text.strip())
    
    return "\n\n".join(text_parts)


@with_error_handling
def extract_txt_text(file_path: FilePath) -> str:
    """Extract text from TXT file with encoding detection."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    # Detect encoding
    detected = chardet.detect(raw_data)
    encoding = detected['encoding'] or 'utf-8'
    
    # Decode with detected encoding
    text = raw_data.decode(encoding, errors='replace')
    return text


class TextExtractor:
    """Main text extraction orchestrator."""
    
    def __init__(self, storage_url: str, redis_url: str):
        self.storage_url = storage_url
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.http_client = httpx.AsyncClient()
        
        # Map file extensions to extractors
        self.extractors = {
            '.pdf': extract_pdf_text,
            '.epub': extract_epub_text,
            '.txt': extract_txt_text,
        }
    
    async def extract_text(self, file_path: FilePath, book_id: BookId) -> ExtractionResult:
        """Extract text from file based on its extension."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return ExtractionResult(success=False, error="File not found")
        
        extractor = self.extractors.get(file_path.suffix.lower())
        if not extractor:
            return ExtractionResult(
                success=False, 
                error=f"Unsupported file format: {file_path.suffix}"
            )
        
        logger.info(f"Extracting text from {file_path} for book {book_id}")
        result = extractor(file_path)
        
        if result.success and result.text:
            # Store extracted text
            await self._store_text(book_id, result.text)
            # Trigger next step in pipeline
            await self._trigger_segmentation(book_id)
        
        return result
    
    async def _store_text(self, book_id: BookId, text: str) -> None:
        """Store extracted text to storage service."""
        try:
            response = await self.http_client.post(
                f"{self.storage_url}/books/{book_id}/text",
                json={"text": text}
            )
            response.raise_for_status()
            logger.info(f"Stored text for book {book_id}")
        except Exception as e:
            logger.error(f"Failed to store text for book {book_id}: {e}")
            raise
    
    async def _trigger_segmentation(self, book_id: BookId) -> None:
        """Trigger segmentation service via Redis queue."""
        try:
            import json
            task_data = {
                "book_id": book_id,
                "action": "segment_text"
            }
            task_json = json.dumps(task_data)
            logger.info(f"Sending to segment_queue: {task_json}")
            self.redis_client.lpush("segment_queue", task_json)
            logger.info(f"Triggered segmentation for book {book_id}")
        except Exception as e:
            logger.error(f"Failed to trigger segmentation for book {book_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the ingest service."""
        try:
            self.redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        try:
            response = await self.http_client.get(f"{self.storage_url}/health")
            storage_status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            storage_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy",
            "service": "ingest",
            "redis": redis_status,
            "storage": storage_status,
            "version": "1.0.0"
        }


async def process_ingest_queue(extractor: TextExtractor):
    """Process the ingest queue continuously."""
    logger.info("Starting ingest queue processing")
    
    while True:
        try:
            # Check for new tasks in the queue
            task_data = extractor.redis_client.brpop("ingest_queue", timeout=30)
            
            if task_data:
                queue_name, task_json = task_data
                logger.info(f"Processing ingest task: {task_json}")
                
                try:
                    import json
                    task = json.loads(task_json)  # Parse the task data
                    book_id = task.get("book_id")
                    file_path = task.get("file_path")
                    
                    if book_id and file_path:
                        # Extract text from the file
                        result = await extractor.extract_text(file_path, book_id)
                        
                        # Send completion notification
                        completion_data = {
                            "book_id": book_id,
                            "success": result.success,
                            "error": result.error
                        }
                        
                        extractor.redis_client.lpush(
                            "ingest_completed", 
                            json.dumps(completion_data)
                        )
                        
                        if result.success:
                            logger.info(f"Successfully processed book {book_id}")
                        else:
                            logger.error(f"Failed to process book {book_id}: {result.error}")
                    
                except Exception as e:
                    logger.error(f"Error processing ingest task: {e}")
                    # Send failure notification
                    try:
                        completion_data = {
                            "book_id": task.get("book_id", "unknown"),
                            "success": False,
                            "error": str(e)
                        }
                        extractor.redis_client.lpush(
                            "ingest_completed", 
                            json.dumps(completion_data)
                        )
                    except:
                        pass
        
        except Exception as e:
            logger.error(f"Error in ingest queue processing: {e}")
            await asyncio.sleep(10)  # Wait before retrying


async def main():
    """Main function for the ingest service."""
    logger.info("Starting Audiobook Ingest Service")
    
    # Initialize extractor
    extractor = TextExtractor(
        storage_url=os.getenv("STORAGE_URL", "http://storage:8001"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    
    # Health check
    health = await extractor.health_check()
    logger.info(f"Health status: {health}")
    
    logger.info("Ingest service ready")
    
    # Start queue processing
    await process_ingest_queue(extractor)


if __name__ == "__main__":
    asyncio.run(main()) 