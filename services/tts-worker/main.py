"""TTS Worker Service for Audiobook Server."""

import os
import json
import asyncio
import logging
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

import redis
import httpx
import torch
import soundfile as sf
import numpy as np
from TTS.api import TTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents a generated audio chunk."""
    seq: int
    text: str
    ssml: str
    audio_data: np.ndarray
    sample_rate: int
    duration_s: float
    file_path: Optional[str] = None


class TTSEngine:
    """Handles text-to-speech generation using Coqui TTS."""
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        """Initialize the TTS engine with specified model."""
        self.model_name = model_name
        self.tts = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"TTS Engine will use device: {self.device}")
    
    def initialize(self):
        """Initialize the TTS model (called once at startup)."""
        try:
            logger.info(f"Loading TTS model: {self.model_name}")
            self.tts = TTS(model_name=self.model_name).to(self.device)
            logger.info("TTS model loaded successfully")
            
            # Test the model with a simple phrase
            test_audio = self.tts.tts("Hello world")
            logger.info(f"TTS model test successful, output shape: {np.array(test_audio).shape}")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS model: {e}")
            raise
    
    def synthesize_text(self, text: str, ssml: str = None) -> AudioChunk:
        """
        Synthesize speech from text or SSML.
        
        Args:
            text: Plain text content
            ssml: SSML markup (if available)
            
        Returns:
            AudioChunk with generated audio data
        """
        try:
            # For now, use plain text (SSML support can be added later)
            # Coqui TTS doesn't have native SSML support, so we'll use the plain text
            input_text = self._clean_text_for_tts(text)
            
            logger.info(f"Synthesizing text: '{input_text[:50]}...' ({len(input_text)} chars)")
            
            # Generate audio
            audio_data = self.tts.tts(input_text)
            
            # Convert to numpy array if needed
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
            
            # Calculate duration
            sample_rate = self.tts.synthesizer.output_sample_rate
            duration_s = len(audio_data) / sample_rate
            
            logger.info(f"Generated audio: {duration_s:.2f}s, {len(audio_data)} samples at {sample_rate}Hz")
            
            return AudioChunk(
                seq=0,  # Will be set by caller
                text=text,
                ssml=ssml or "",
                audio_data=audio_data,
                sample_rate=sample_rate,
                duration_s=duration_s
            )
            
        except Exception as e:
            logger.error(f"Failed to synthesize text: {e}")
            raise
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS processing."""
        # Remove or replace characters that might cause issues
        cleaned = text.strip()
        
        # Replace multiple whitespace with single space
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Ensure text ends with punctuation for better prosody
        if cleaned and cleaned[-1] not in '.!?':
            cleaned += '.'
        
        return cleaned
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the TTS engine."""
        try:
            if self.tts is None:
                return {"status": "unhealthy", "error": "TTS model not initialized"}
            
            # Quick synthesis test
            test_audio = self.tts.tts("Test")
            return {
                "status": "healthy",
                "model": self.model_name,
                "device": self.device,
                "sample_rate": self.tts.synthesizer.output_sample_rate
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class TTSWorker:
    """Handles the TTS processing pipeline."""
    
    def __init__(self):
        """Initialize the TTS worker."""
        self.storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        self.http_client = httpx.AsyncClient()
        
        # Initialize TTS engine
        model_name = os.getenv("TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
        self.tts_engine = TTSEngine(model_name)
        
        # Audio output settings
        self.wav_data_path = Path(os.getenv("WAV_DATA_PATH", "/data/wav"))
        self.wav_data_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the TTS worker (call once at startup)."""
        logger.info("Initializing TTS Worker")
        
        # Initialize TTS engine in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.tts_engine.initialize)
        
        logger.info("TTS Worker initialization complete")
    
    async def process_tts_queue(self):
        """Process the TTS queue continuously."""
        logger.info("Starting TTS queue processing")
        
        while True:
            try:
                # Check for new tasks in the queue (blocking with timeout)
                task_data = self.redis_client.brpop("tts_queue", timeout=30)
                
                if task_data:
                    queue_name, task_json = task_data
                    logger.info(f"Processing TTS task: {task_json}")
                    
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
                                "error": None if success else "TTS generation failed"
                            }
                            
                            self.redis_client.lpush(
                                "tts_completed",
                                json.dumps(completion_data)
                            )
                            
                            if success:
                                logger.info(f"Successfully generated audio for book {book_id}")
                            else:
                                logger.error(f"Failed to generate audio for book {book_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing TTS task: {e}")
                        # Send failure notification
                        try:
                            completion_data = {
                                "book_id": task.get("book_id", "unknown"),
                                "success": False,
                                "error": str(e)
                            }
                            self.redis_client.lpush(
                                "tts_completed",
                                json.dumps(completion_data)
                            )
                        except:
                            pass
            
            except Exception as e:
                logger.error(f"Error in TTS queue processing: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _process_book(self, book_id: str) -> bool:
        """
        Process a book for TTS generation.
        
        Args:
            book_id: The book ID to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing book {book_id} for TTS generation")
            
            # Get SSML chunks from storage service
            chunks_data = await self._get_book_chunks(book_id)
            if not chunks_data:
                logger.error(f"No chunks found for book {book_id}")
                return False
            
            # Generate audio for each chunk
            audio_chunks = []
            for chunk_data in chunks_data:
                audio_chunk = await self._generate_chunk_audio(chunk_data)
                if audio_chunk:
                    audio_chunks.append(audio_chunk)
                else:
                    logger.error(f"Failed to generate audio for chunk {chunk_data.get('seq', 'unknown')}")
                    return False
            
            # Save audio chunks to storage
            await self._save_audio_chunks(book_id, audio_chunks)
            
            # Trigger transcoding
            await self._trigger_transcoding(book_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing book {book_id}: {e}")
            return False
    
    async def _get_book_chunks(self, book_id: str) -> List[Dict[str, Any]]:
        """Get SSML chunks for a book from storage service."""
        try:
            # For now, we'll read directly from the file system
            # In a production system, this could be an API call
            chunks_dir = Path(f"/data/text/{book_id}/chunks")
            if not chunks_dir.exists():
                logger.error(f"Chunks directory not found: {chunks_dir}")
                return []
            
            chunks_data = []
            
            # Find all chunk metadata files
            for metadata_file in sorted(chunks_dir.glob("chunk_*.json")):
                try:
                    with open(metadata_file, 'r') as f:
                        chunk_metadata = json.load(f)
                    
                    # Read the SSML content
                    ssml_file = chunks_dir / f"chunk_{chunk_metadata['seq']:03d}.ssml"
                    if ssml_file.exists():
                        with open(ssml_file, 'r') as f:
                            ssml_content = f.read()
                        
                        chunk_metadata['ssml'] = ssml_content
                        chunks_data.append(chunk_metadata)
                    
                except Exception as e:
                    logger.error(f"Error reading chunk metadata {metadata_file}: {e}")
                    continue
            
            logger.info(f"Found {len(chunks_data)} chunks for book {book_id}")
            return chunks_data
            
        except Exception as e:
            logger.error(f"Failed to get chunks for book {book_id}: {e}")
            return []
    
    async def _generate_chunk_audio(self, chunk_data: Dict[str, Any]) -> Optional[AudioChunk]:
        """Generate audio for a single chunk."""
        try:
            seq = chunk_data['seq']
            text = chunk_data['text']
            ssml = chunk_data.get('ssml', '')
            
            logger.info(f"Generating audio for chunk {seq}")
            
            # Generate audio in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            audio_chunk = await loop.run_in_executor(
                None, 
                self.tts_engine.synthesize_text, 
                text, 
                ssml
            )
            
            # Set the sequence number
            audio_chunk.seq = seq
            
            return audio_chunk
            
        except Exception as e:
            logger.error(f"Failed to generate audio for chunk: {e}")
            return None
    
    async def _save_audio_chunks(self, book_id: str, audio_chunks: List[AudioChunk]):
        """Save generated audio chunks to storage."""
        try:
            # Create book-specific directory
            book_wav_dir = self.wav_data_path / book_id
            book_wav_dir.mkdir(parents=True, exist_ok=True)
            
            for chunk in audio_chunks:
                # Save as WAV file
                wav_file = book_wav_dir / f"chunk_{chunk.seq:03d}.wav"
                sf.write(str(wav_file), chunk.audio_data, chunk.sample_rate)
                
                # Update chunk with file path
                chunk.file_path = str(wav_file)
                
                logger.info(f"Saved audio chunk {chunk.seq}: {wav_file} ({chunk.duration_s:.2f}s)")
            
            # Store chunk metadata (could be sent to storage service API)
            metadata = []
            for chunk in audio_chunks:
                metadata.append({
                    "seq": chunk.seq,
                    "duration_s": chunk.duration_s,
                    "sample_rate": chunk.sample_rate,
                    "file_path": chunk.file_path,
                    "file_size": os.path.getsize(chunk.file_path) if chunk.file_path else 0
                })
            
            # Save metadata file
            metadata_file = book_wav_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved {len(audio_chunks)} audio chunks for book {book_id}")
            
        except Exception as e:
            logger.error(f"Failed to save audio chunks for book {book_id}: {e}")
            raise
    
    async def _trigger_transcoding(self, book_id: str):
        """Trigger transcoding service for the book."""
        try:
            transcode_task = {
                "book_id": book_id,
                "action": "transcode_audio"
            }
            
            self.redis_client.lpush("transcode_queue", json.dumps(transcode_task))
            logger.info(f"Triggered transcoding for book {book_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger transcoding for book {book_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the TTS worker."""
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
        
        # Check TTS engine
        tts_status = self.tts_engine.health_check()
        
        return {
            "status": "healthy",
            "service": "tts-worker",
            "redis": redis_status,
            "storage": storage_status,
            "tts_engine": tts_status,
            "version": "1.0.0"
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()


async def main():
    """Main function for the TTS worker service."""
    logger.info("Starting Audiobook TTS Worker Service")
    
    # Initialize worker
    worker = TTSWorker()
    
    # Initialize TTS engine
    await worker.initialize()
    
    # Health check
    health = await worker.health_check()
    logger.info(f"Health status: {health}")
    
    logger.info("TTS Worker service ready")
    
    # Start queue processing
    try:
        await worker.process_tts_queue()
    finally:
        await worker.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 