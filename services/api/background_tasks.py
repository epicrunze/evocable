"""Background task management for audiobook processing pipeline."""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
import redis
from models import DatabaseManager, BookStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Manages the audiobook processing pipeline."""
    
    def __init__(self):
        self.db_manager = DatabaseManager(
            db_path=os.getenv("DATABASE_PATH", "/data/meta/audiobooks.db")
        )
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        self.http_client = httpx.AsyncClient()
        self.storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        self.ingest_url = os.getenv("INGEST_URL", "http://ingest:8002")
        
    async def start_processing(self, book_id: str, file_path: str) -> None:
        """Start the processing pipeline for a book."""
        try:
            logger.info(f"Starting processing pipeline for book {book_id}")
            
            # Update status to processing
            self.db_manager.update_book_status(
                book_id=book_id,
                status=BookStatus.PROCESSING.value,
                percent_complete=5.0
            )
            
            # Trigger ingest service
            await self._trigger_ingest(book_id, file_path)
            
        except Exception as e:
            logger.error(f"Failed to start processing for book {book_id}: {e}")
            self.db_manager.update_book_status(
                book_id=book_id,
                status=BookStatus.FAILED.value,
                error_message=f"Failed to start processing: {str(e)}"
            )
    
    async def _trigger_ingest(self, book_id: str, file_path: str) -> None:
        """Trigger the ingest service to extract text."""
        try:
            logger.info(f"Triggering ingest for book {book_id}")
            
            # Update status to extracting
            self.db_manager.update_book_status(
                book_id=book_id,
                status=BookStatus.EXTRACTING.value,
                percent_complete=10.0
            )
            
            # Add to ingest queue via Redis
            import json
            ingest_task = {
                "book_id": book_id,
                "file_path": file_path,
                "action": "extract_text"
            }
            
            self.redis_client.lpush("ingest_queue", json.dumps(ingest_task))
            logger.info(f"Added book {book_id} to ingest queue")
            
        except Exception as e:
            logger.error(f"Failed to trigger ingest for book {book_id}: {e}")
            raise
    
    async def monitor_progress(self) -> None:
        """Monitor processing progress and update book statuses."""
        logger.info("Starting progress monitoring")
        
        while True:
            try:
                await self._check_pipeline_progress()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in progress monitoring: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _check_pipeline_progress(self) -> None:
        """Check progress of books in the pipeline."""
        try:
            # Check for completed ingest tasks
            await self._check_ingest_completion()
            
            # Check for completed segmentation tasks
            await self._check_segmentation_completion()
            
            # Check for completed TTS tasks
            await self._check_tts_completion()
            
            # Check for completed transcoding tasks
            await self._check_transcoding_completion()
            
        except Exception as e:
            logger.error(f"Error checking pipeline progress: {e}")
    
    async def _check_ingest_completion(self) -> None:
        """Check for completed ingest tasks."""
        completed_task = self.redis_client.rpop("ingest_completed")
        if completed_task:
            try:
                # Parse the completed task (assuming JSON format)
                import json
                task_data = json.loads(completed_task)
                book_id = task_data.get("book_id")
                
                if task_data.get("success"):
                    logger.info(f"Ingest completed for book {book_id}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.SEGMENTING.value,
                        percent_complete=25.0
                    )
                else:
                    logger.error(f"Ingest failed for book {book_id}: {task_data.get('error')}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.FAILED.value,
                        error_message=task_data.get("error", "Ingest failed")
                    )
            except Exception as e:
                logger.error(f"Error processing ingest completion: {e}")
    
    async def _check_segmentation_completion(self) -> None:
        """Check for completed segmentation tasks."""
        completed_task = self.redis_client.rpop("segment_completed")
        if completed_task:
            try:
                import json
                task_data = json.loads(completed_task)
                book_id = task_data.get("book_id")
                
                if task_data.get("success"):
                    logger.info(f"Segmentation completed for book {book_id}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.GENERATING_AUDIO.value,
                        percent_complete=50.0
                    )
                else:
                    logger.error(f"Segmentation failed for book {book_id}: {task_data.get('error')}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.FAILED.value,
                        error_message=task_data.get("error", "Segmentation failed")
                    )
            except Exception as e:
                logger.error(f"Error processing segmentation completion: {e}")
    
    async def _check_tts_completion(self) -> None:
        """Check for completed TTS tasks."""
        completed_task = self.redis_client.rpop("tts_completed")
        if completed_task:
            try:
                import json
                task_data = json.loads(completed_task)
                book_id = task_data.get("book_id")
                
                if task_data.get("success"):
                    logger.info(f"TTS completed for book {book_id}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.TRANSCODING.value,
                        percent_complete=75.0
                    )
                else:
                    logger.error(f"TTS failed for book {book_id}: {task_data.get('error')}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.FAILED.value,
                        error_message=task_data.get("error", "TTS generation failed")
                    )
            except Exception as e:
                logger.error(f"Error processing TTS completion: {e}")
    
    async def _check_transcoding_completion(self) -> None:
        """Check for completed transcoding tasks."""
        completed_task = self.redis_client.rpop("transcode_completed")
        if completed_task:
            try:
                import json
                task_data = json.loads(completed_task)
                book_id = task_data.get("book_id")
                
                if task_data.get("success"):
                    logger.info(f"Transcoding completed for book {book_id}")
                    
                    # Get chunk count from task data
                    total_chunks = task_data.get("total_chunks", 0)
                    
                    # Update chunks in database
                    await self._update_chunks_metadata(book_id, task_data.get("chunks", []))
                    
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.COMPLETED.value,
                        percent_complete=100.0,
                        total_chunks=total_chunks
                    )
                else:
                    logger.error(f"Transcoding failed for book {book_id}: {task_data.get('error')}")
                    self.db_manager.update_book_status(
                        book_id=book_id,
                        status=BookStatus.FAILED.value,
                        error_message=task_data.get("error", "Transcoding failed")
                    )
            except Exception as e:
                logger.error(f"Error processing transcoding completion: {e}")
    
    async def _update_chunks_metadata(self, book_id: str, chunks_data: list) -> None:
        """Update chunk metadata in the database."""
        try:
            for chunk_info in chunks_data:
                self.db_manager.create_chunk(
                    book_id=book_id,
                    seq=chunk_info.get("seq"),
                    duration_s=chunk_info.get("duration_s"),
                    file_path=chunk_info.get("file_path"),
                    file_size=chunk_info.get("file_size")
                )
            logger.info(f"Updated {len(chunks_data)} chunks for book {book_id}")
        except Exception as e:
            logger.error(f"Error updating chunks metadata for book {book_id}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the processing pipeline."""
        try:
            self.redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        try:
            # Check database
            test_book = self.db_manager.get_book("health-check")
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        return {
            "redis": redis_status,
            "database": db_status,
            "pipeline": "ready"
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.http_client.aclose()


# Global pipeline instance
pipeline = ProcessingPipeline() 