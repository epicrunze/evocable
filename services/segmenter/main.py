"""Text segmentation service for Audiobook Server.

This service segments extracted text into speech-ready chunks with SSML markup.
It uses spaCy for natural language processing and intelligent sentence boundaries.
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

import redis.asyncio as redis
import httpx
import spacy
from dataclasses import dataclass

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""
    seq: int
    text: str
    ssml: str
    char_count: int


class TextSegmenter:
    """Handles text segmentation and SSML generation."""
    
    def __init__(self, max_chunk_size: int = 800):
        """Initialize the text segmenter with spaCy model."""
        self.max_chunk_size = max_chunk_size
        logger.info("Loading spaCy English model...")
        
        try:
            # Load the spaCy model
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except OSError as e:
            logger.error(f"Failed to load spaCy model: {e}")
            # Fallback to basic English tokenizer
            from spacy.lang.en import English
            self.nlp = English()
            self.nlp.add_pipe('sentencizer')
            logger.warning("Using fallback sentencizer")
    
    def segment_text(self, text: str) -> List[TextChunk]:
        """
        Segment text into chunks with SSML markup.
        
        Args:
            text: Raw text to segment
            
        Returns:
            List of TextChunk objects with SSML markup
        """
        logger.info(f"Segmenting text of {len(text)} characters")
        
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Extract sentences
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        logger.info(f"Found {len(sentences)} sentences")
        
        # Group sentences into chunks
        chunks = self._create_chunks(sentences)
        
        # Generate SSML for each chunk
        text_chunks = []
        for i, chunk_sentences in enumerate(chunks):
            chunk_text = " ".join(chunk_sentences)
            ssml = self._generate_ssml(chunk_sentences)
            
            text_chunks.append(TextChunk(
                seq=i,
                text=chunk_text,
                ssml=ssml,
                char_count=len(chunk_text)
            ))
        
        logger.info(f"Created {len(text_chunks)} chunks")
        return text_chunks
    
    def _create_chunks(self, sentences: List[str]) -> List[List[str]]:
        """
        Group sentences into chunks respecting max_chunk_size.
        
        Args:
            sentences: List of sentence strings
            
        Returns:
            List of sentence groups (chunks)
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed max size, start new chunk
            if current_chunk and (current_size + sentence_length + 1) > self.max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = [sentence]
                current_size = sentence_length
            else:
                current_chunk.append(sentence)
                current_size += sentence_length + (1 if current_chunk else 0)  # +1 for space
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _generate_ssml(self, sentences: List[str]) -> str:
        """
        Generate SSML markup for a list of sentences.
        
        Args:
            sentences: List of sentences to mark up
            
        Returns:
            SSML-formatted string
        """
        ssml_parts = ['<speak>']
        
        for i, sentence in enumerate(sentences):
            # Clean the sentence
            clean_sentence = sentence.strip()
            if not clean_sentence:
                continue
            
            # Wrap each sentence in <s> tags
            ssml_parts.append(f'<s>{clean_sentence}</s>')
            
            # Add a short break between sentences (except for the last one)
            if i < len(sentences) - 1:
                ssml_parts.append('<break time="0.3s"/>')
        
        ssml_parts.append('</speak>')
        return ''.join(ssml_parts)


class SegmentationProcessor:
    """Handles the segmentation processing pipeline."""
    
    def __init__(self):
        """Initialize the segmentation processor."""
        self.storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        self.http_client = httpx.AsyncClient()
        self.segmenter = TextSegmenter(
            max_chunk_size=int(os.getenv("CHUNK_SIZE_CHARS", "800"))
        )
    
    async def process_segmentation_queue(self):
        """Process the segmentation queue continuously."""
        logger.info("Starting segmentation queue processing")
        
        while True:
            try:
                # Check for new tasks in the queue (blocking with timeout)
                task_data = await self.redis_client.brpop("segment_queue", timeout=30)
                
                if task_data:
                    queue_name, task_json = task_data
                    logger.info(f"Processing segmentation task: {task_json}")
                    logger.info(f"Task JSON type: {type(task_json)}, length: {len(task_json)}")
                    
                    try:
                        task = json.loads(task_json)
                        book_id = task.get("book_id")
                        
                        if book_id:
                            # Process the book
                            success = await self._process_book(book_id)
                            
                            # Send completion notification
                            completion_data = {
                                "book_id": book_id,
                                "success": success,
                                "error": None if success else "Segmentation failed"
                            }
                            
                            await self.redis_client.lpush(
                                "segment_completed",
                                json.dumps(completion_data)
                            )
                            
                            if success:
                                logger.info(f"Successfully segmented book {book_id}")
                            else:
                                logger.error(f"Failed to segment book {book_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing segmentation task: {e}")
                        # Send failure notification
                        try:
                            completion_data = {
                                "book_id": task.get("book_id", "unknown"),
                                "success": False,
                                "error": str(e)
                            }
                            await self.redis_client.lpush(
                                "segment_completed",
                                json.dumps(completion_data)
                            )
                        except:
                            pass
            
            except Exception as e:
                logger.error(f"Error in segmentation queue processing: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _process_book(self, book_id: str) -> bool:
        """
        Process a book for segmentation.
        
        Args:
            book_id: The book ID to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing book {book_id} for segmentation")
            
            # Get text from storage service
            text = await self._get_book_text(book_id)
            if not text:
                logger.error(f"No text found for book {book_id}")
                return False
            
            # Segment the text
            chunks = self.segmenter.segment_text(text)
            if not chunks:
                logger.error(f"No chunks generated for book {book_id}")
                return False
            
            # Store SSML chunks
            await self._store_chunks(book_id, chunks)
            
            # Trigger TTS processing
            await self._trigger_tts(book_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing book {book_id}: {e}")
            return False
    
    async def _get_book_text(self, book_id: str) -> Optional[str]:
        """Get book text from storage service."""
        try:
            response = await self.http_client.get(
                f"{self.storage_url}/books/{book_id}/text"
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("text")
            
        except Exception as e:
            logger.error(f"Failed to get text for book {book_id}: {e}")
            return None
    
    async def _store_chunks(self, book_id: str, chunks: List[TextChunk]):
        """Store SSML chunks to storage service."""
        try:
            # Prepare chunk data for storage
            chunks_data = []
            for chunk in chunks:
                chunks_data.append({
                    "seq": chunk.seq,
                    "text": chunk.text,
                    "ssml": chunk.ssml,
                    "char_count": chunk.char_count
                })
            
            # Send to storage service
            response = await self.http_client.post(
                f"{self.storage_url}/books/{book_id}/chunks",
                json={"chunks": chunks_data}
            )
            response.raise_for_status()
            
            logger.info(f"Stored {len(chunks)} chunks for book {book_id}")
            
        except Exception as e:
            logger.error(f"Failed to store chunks for book {book_id}: {e}")
            raise
    
    async def _trigger_tts(self, book_id: str):
        """Trigger TTS processing for the book."""
        try:
            tts_task = {
                "book_id": book_id,
                "action": "generate_audio"
            }
            
            await self.redis_client.lpush("tts_queue", json.dumps(tts_task))
            logger.info(f"Triggered TTS processing for book {book_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger TTS for book {book_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the segmentation processor."""
        try:
            await self.redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
        try:
            response = await self.http_client.get(f"{self.storage_url}/health")
            storage_status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            storage_status = f"unhealthy: {str(e)}"
        
        # Check spaCy model
        try:
            # Test spaCy processing
            test_doc = self.segmenter.nlp("Test sentence.")
            spacy_status = "healthy"
        except Exception as e:
            spacy_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy",
            "service": "segmenter",
            "redis": redis_status,
            "storage": storage_status,
            "spacy": spacy_status,
            "version": "1.0.0"
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()


async def main():
    """Main function for the segmenter service."""
    logger.info("Starting Audiobook Segmenter Service")
    
    # Initialize processor
    processor = SegmentationProcessor()
    
    # Health check
    health = await processor.health_check()
    logger.info(f"Health status: {health}")
    
    logger.info("Segmenter service ready")
    
    # Start queue processing
    try:
        await processor.process_segmentation_queue()
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 