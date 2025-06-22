"""FastAPI application for Audiobook Server API Gateway."""

import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import httpx

# Import our data models
from models import (
    DatabaseManager, 
    BookSubmissionRequest, 
    BookResponse, 
    BookStatusResponse,
    ChunkListResponse,
    ErrorResponse,
    BookStatus
)

# Security
security = HTTPBearer()

# Initialize FastAPI app
app = FastAPI(
    title="Audiobook Server API",
    description="Convert PDF, EPUB, and TXT files to streaming audiobooks",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# HTTP client for service communication
http_client = httpx.AsyncClient()

# Database manager
db_manager = DatabaseManager(
    db_path=os.getenv("DATABASE_PATH", "/data/meta/audiobooks.db")
)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Authorization header."""
    api_key = os.getenv("API_KEY", "default-dev-key")
    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        # Check Redis connection
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    try:
        # Check database connection
        test_book = db_manager.get_book("test-health-check")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "api",
        "redis": redis_status,
        "database": db_status,
        "version": "1.0.0"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Audiobook Server API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Placeholder endpoints for Phase 2 implementation
# These will be implemented in the next phase

@app.post("/api/v1/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def submit_book():
    """Submit a book for processing - TO BE IMPLEMENTED."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )


@app.get("/api/v1/books/{book_id}/status", response_model=BookStatusResponse)
async def get_book_status(book_id: str):
    """Get book processing status - TO BE IMPLEMENTED."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )


@app.get("/api/v1/books/{book_id}/chunks", response_model=ChunkListResponse)
async def list_book_chunks(book_id: str):
    """List available audio chunks for a book - TO BE IMPLEMENTED."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )


@app.get("/api/v1/books/{book_id}/chunks/{seq}")
async def get_audio_chunk(book_id: str, seq: int):
    """Stream an audio chunk - TO BE IMPLEMENTED."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Endpoint not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 