"""Audio transcoding service for Audiobook Server."""

import os
import logging
from typing import Dict, Any

import redis
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# HTTP client for storage service communication
http_client = httpx.AsyncClient()


async def health_check() -> Dict[str, Any]:
    """Health check for the transcoder service."""
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    try:
        # Check storage service connection
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        response = await http_client.get(f"{storage_url}/health")
        storage_status = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"
    
    # Check FFmpeg availability
    try:
        import subprocess
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


async def main():
    """Main function for the transcoder service."""
    logger.info("Starting Audiobook Transcoder Service")
    
    # Health check
    health = await health_check()
    logger.info(f"Health status: {health}")
    
    # TODO: Implement audio transcoding logic
    # - WAV to Opus conversion
    # - Audio segmentation (3.14s chunks)
    # - Ogg container packaging
    # - Metadata updates
    
    logger.info("Transcoder service ready")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 