"""Audio transcoding service for Audiobook Server."""

import os
import json
import asyncio
import logging
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

import redis
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioTranscoder:
    """Handles audio transcoding from WAV to streaming Opus format."""
    
    def __init__(self):
        """Initialize the transcoder."""
        self.storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        self.redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        self.http_client = httpx.AsyncClient()
        
        # Transcoding settings
        self.segment_duration = float(os.getenv("SEGMENT_DURATION", "3.14"))
        self.opus_bitrate = os.getenv("OPUS_BITRATE", "32k")
        
        # Data paths
        self.wav_data_path = Path(os.getenv("WAV_DATA_PATH", "/data/wav"))
        self.ogg_data_path = Path(os.getenv("SEGMENT_DATA_PATH", "/data/ogg"))
        self.ogg_data_path.mkdir(parents=True, exist_ok=True)
    
    async def process_transcode_queue(self):
        """Process the transcoding queue continuously."""
        logger.info("Starting transcoding queue processing")
        
        while True:
            try:
                # Check for new tasks in the queue (blocking with timeout)
                task_data = self.redis_client.brpop("transcode_queue", timeout=30)
                
                if task_data:
                    queue_name, task_json = task_data
                    logger.info(f"Processing transcode task: {task_json}")
                    
                    try:
                        task = json.loads(task_json)
                        book_id = task.get("book_id")
                        
                        if book_id:
                            # Process the book
                            success = await self._transcode_book(book_id)
                            
                            # Send completion notification
                            completion_data = {
                                "book_id": book_id,
                                "success": success,
                                "error": None if success else "Transcoding failed"
                            }
                            
                            self.redis_client.lpush(
                                "transcode_completed",
                                json.dumps(completion_data)
                            )
                            
                            if success:
                                logger.info(f"Successfully transcoded book {book_id}")
                            else:
                                logger.error(f"Failed to transcode book {book_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing transcode task: {e}")
                        # Send failure notification
                        try:
                            completion_data = {
                                "book_id": task.get("book_id", "unknown"),
                                "success": False,
                                "error": str(e)
                            }
                            self.redis_client.lpush(
                                "transcode_completed",
                                json.dumps(completion_data)
                            )
                        except:
                            pass
            
            except Exception as e:
                logger.error(f"Error in transcode queue processing: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _transcode_book(self, book_id: str) -> bool:
        """
        Transcode a book's WAV files to streaming Opus format.
        
        Args:
            book_id: The book ID to transcode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Transcoding book {book_id}")
            
            # Get WAV files for the book
            wav_files = await self._get_wav_files(book_id)
            if not wav_files:
                logger.error(f"No WAV files found for book {book_id}")
                return False
            
            # Create output directory
            book_ogg_dir = self.ogg_data_path / book_id
            book_ogg_dir.mkdir(parents=True, exist_ok=True)
            
            # Transcode each WAV file
            transcoded_chunks = []
            for wav_file_info in wav_files:
                chunks = await self._transcode_wav_file(wav_file_info, book_ogg_dir)
                if chunks:
                    transcoded_chunks.extend(chunks)
                else:
                    logger.error(f"Failed to transcode WAV file {wav_file_info['file_path']}")
                    return False
            
            # Update storage service with chunk information
            await self._update_chunk_metadata(book_id, transcoded_chunks)
            
            logger.info(f"Successfully transcoded {len(transcoded_chunks)} chunks for book {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error transcoding book {book_id}: {e}")
            return False
    
    async def _get_wav_files(self, book_id: str) -> List[Dict[str, Any]]:
        """Get WAV file information for a book."""
        try:
            # Read WAV metadata file
            wav_metadata_file = self.wav_data_path / book_id / "metadata.json"
            if not wav_metadata_file.exists():
                logger.error(f"WAV metadata file not found: {wav_metadata_file}")
                return []
            
            with open(wav_metadata_file, 'r') as f:
                wav_files = json.load(f)
            
            logger.info(f"Found {len(wav_files)} WAV files for book {book_id}")
            return wav_files
            
        except Exception as e:
            logger.error(f"Failed to get WAV files for book {book_id}: {e}")
            return []
    
    async def _transcode_wav_file(self, wav_file_info: Dict[str, Any], output_dir: Path) -> List[Dict[str, Any]]:
        """
        Transcode a single WAV file to segmented Opus format.
        
        Args:
            wav_file_info: WAV file metadata
            output_dir: Output directory for Opus files
            
        Returns:
            List of transcoded chunk information
        """
        try:
            wav_file_path = Path(wav_file_info["file_path"])
            seq = wav_file_info["seq"]
            duration_s = wav_file_info["duration_s"]
            
            logger.info(f"Transcoding WAV file: {wav_file_path} ({duration_s:.2f}s)")
            
            # Calculate number of segments needed
            num_segments = int(duration_s / self.segment_duration) + 1
            
            chunks = []
            for segment_idx in range(num_segments):
                start_time = segment_idx * self.segment_duration
                
                # Calculate actual segment duration (last segment might be shorter)
                actual_duration = min(self.segment_duration, duration_s - start_time)
                if actual_duration <= 0:
                    break
                
                # Generate output filename
                chunk_seq = seq * 1000 + segment_idx  # Unique sequence across all chunks
                output_file = output_dir / f"chunk_{chunk_seq:06d}.ogg"
                
                # FFmpeg command for transcoding
                cmd = [
                    "ffmpeg", "-y",  # Overwrite output files
                    "-i", str(wav_file_path),  # Input WAV file
                    "-ss", str(start_time),  # Start time
                    "-t", str(actual_duration),  # Duration
                    "-c:a", "libopus",  # Opus codec
                    "-b:a", self.opus_bitrate,  # Bitrate
                    "-vbr", "on",  # Variable bitrate
                    "-compression_level", "10",  # Best compression
                    "-frame_duration", "20",  # 20ms frames
                    "-application", "voip",  # Optimized for speech
                    str(output_file)
                ]
                
                # Execute FFmpeg
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg failed for segment {segment_idx}: {stderr.decode()}")
                    return []
                
                # Get file size
                file_size = output_file.stat().st_size if output_file.exists() else 0
                
                chunk_info = {
                    "seq": chunk_seq,
                    "duration_s": actual_duration,
                    "file_path": str(output_file),
                    "file_size": file_size,
                    "format": "opus",
                    "container": "ogg",
                    "bitrate": self.opus_bitrate
                }
                
                chunks.append(chunk_info)
                logger.info(f"Created chunk {chunk_seq}: {output_file.name} ({actual_duration:.2f}s, {file_size} bytes)")
            
            logger.info(f"Transcoded WAV file into {len(chunks)} Opus chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to transcode WAV file: {e}")
            return []
    
    async def _update_chunk_metadata(self, book_id: str, chunks: List[Dict[str, Any]]):
        """Update the storage service with transcoded chunk metadata."""
        try:
            # For now, we'll save metadata locally
            # In a production system, this would be an API call to storage service
            metadata_file = self.ogg_data_path / book_id / "metadata.json"
            
            with open(metadata_file, 'w') as f:
                json.dump(chunks, f, indent=2)
            
            logger.info(f"Updated chunk metadata for book {book_id}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to update chunk metadata for book {book_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the transcoder."""
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
        
        # Check FFmpeg availability
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            ffmpeg_status = "available" if result.returncode == 0 else "unavailable"
        except Exception as e:
            ffmpeg_status = f"error: {str(e)}"
        
        return {
            "status": "healthy",
            "service": "transcoder",
            "redis": redis_status,
            "storage": storage_status,
            "ffmpeg": ffmpeg_status,
            "version": "1.0.0"
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()


async def main():
    """Main function for the transcoder service."""
    logger.info("Starting Audiobook Transcoder Service")
    
    # Initialize transcoder
    transcoder = AudioTranscoder()
    
    # Health check
    health = await transcoder.health_check()
    logger.info(f"Health status: {health}")
    
    logger.info("Transcoder service ready")
    
    # Start queue processing
    try:
        await transcoder.process_transcode_queue()
    finally:
        await transcoder.cleanup()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 