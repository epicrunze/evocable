"""FastAPI application for Audiobook Server API Gateway."""

import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    ChunkInfo,
    ErrorResponse,
    BookStatus,
    BookFormat
)

# Import background task processing
from background_tasks import pipeline

# Security
security = HTTPBearer()

# Background task for monitoring pipeline
pipeline_monitor_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global pipeline_monitor_task
    
    # Startup
    print("Starting Audiobook API service...")
    
    # Start background pipeline monitoring
    pipeline_monitor_task = asyncio.create_task(pipeline.monitor_progress())
    print("Background pipeline monitoring started")
    
    yield
    
    # Shutdown
    print("Shutting down Audiobook API service...")
    
    # Cancel background tasks
    if pipeline_monitor_task:
        pipeline_monitor_task.cancel()
        try:
            await pipeline_monitor_task
        except asyncio.CancelledError:
            pass
    
    # Cleanup pipeline resources
    await pipeline.cleanup()
    print("Shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Audiobook Server API",
    description="Convert PDF, EPUB, and TXT files to streaming audiobooks",
    version="1.0.0",
    lifespan=lifespan
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
    
    # Check pipeline status
    pipeline_status = await pipeline.health_check()
    
    return {
        "status": "healthy",
        "service": "api",
        "redis": redis_status,
        "database": db_status,
        "pipeline": pipeline_status,
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
async def submit_book(
    title: str = Form(..., description="Book title"),
    format: str = Form(..., description="Book format (pdf, epub, txt)"),
    file: UploadFile = File(..., description="Book file to process"),
    api_key: str = Depends(verify_api_key)
):
    """Submit a book for processing."""
    try:
        # Validate format
        try:
            book_format = BookFormat(format.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format. Supported formats: {', '.join([f.value for f in BookFormat])}"
            )
        
        # Validate file type
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        file_extension = Path(file.filename).suffix.lower()
        expected_extension = f".{book_format.value}"
        if file_extension != expected_extension:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension {file_extension} doesn't match format {book_format.value}"
            )
        
        # Validate file size (max 50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum size is 50MB"
            )
        
        # Create book record in database
        book_id = db_manager.create_book(
            title=title,
            format=book_format.value,
            file_path=""  # Will be set after file is saved
        )
        
        # Save file to storage
        book_dir = Path(f"/data/text/{book_id}")
        book_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = book_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Update book record with file path
        db_manager.update_book_status(
            book_id=book_id,
            status=BookStatus.PENDING.value,
            percent_complete=0.0
        )
        
        # Store file path in database (update the record)
        with sqlite3.connect(db_manager.db_path) as conn:
            conn.execute(
                "UPDATE books SET file_path = ? WHERE id = ?",
                (str(file_path), book_id)
            )
            conn.commit()
        
        # Trigger processing pipeline in the background
        asyncio.create_task(pipeline.start_processing(book_id, str(file_path)))
        
        return BookResponse(
            book_id=book_id,
            status=BookStatus.PENDING,
            message=f"Book '{title}' submitted successfully for processing"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process book submission: {str(e)}"
        )


@app.get("/api/v1/books/{book_id}/status", response_model=BookStatusResponse)
async def get_book_status(
    book_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get book processing status."""
    try:
        # Get book from database
        book = db_manager.get_book(book_id)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Get total chunks if completed
        total_chunks = None
        if book["status"] == BookStatus.COMPLETED.value:
            chunks = db_manager.get_chunks(book_id)
            total_chunks = len(chunks)
        elif book["total_chunks"] > 0:
            total_chunks = book["total_chunks"]
        
        return BookStatusResponse(
            book_id=book["id"],
            title=book["title"],
            status=BookStatus(book["status"]),
            percent_complete=book["percent_complete"] or 0.0,
            error_message=book["error_message"],
            created_at=book["created_at"],
            updated_at=book["updated_at"],
            total_chunks=total_chunks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get book status: {str(e)}"
        )


@app.get("/api/v1/books/{book_id}/chunks", response_model=ChunkListResponse)
async def list_book_chunks(
    book_id: str,
    api_key: str = Depends(verify_api_key)
):
    """List available audio chunks for a book."""
    try:
        # Check if book exists
        book = db_manager.get_book(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Get chunks from database
        chunks_data = db_manager.get_chunks(book_id)
        
        # Convert to response format
        chunks = []
        total_duration = 0.0
        
        for chunk_data in chunks_data:
            chunk_url = f"/api/v1/books/{book_id}/chunks/{chunk_data['seq']}"
            chunk_info = ChunkInfo(
                seq=chunk_data["seq"],
                duration_s=chunk_data["duration_s"],
                url=chunk_url,
                file_size=chunk_data.get("file_size")
            )
            chunks.append(chunk_info)
            total_duration += chunk_data["duration_s"]
        
        return ChunkListResponse(
            book_id=book_id,
            total_chunks=len(chunks),
            total_duration_s=total_duration,
            chunks=chunks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list book chunks: {str(e)}"
        )


@app.get("/api/v1/books/{book_id}/chunks/{seq}")
async def get_audio_chunk(
    book_id: str, 
    seq: int,
    api_key: str = Depends(verify_api_key)
):
    """Stream an audio chunk."""
    try:
        # Check if book exists
        book = db_manager.get_book(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Get specific chunk
        chunk = db_manager.get_chunk(book_id, seq)
        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {seq} not found for book {book_id}"
            )
        
        # Check if audio file exists
        audio_file_path = Path(chunk["file_path"])
        if not audio_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {chunk['file_path']}"
            )
        
        # Return file response
        return FileResponse(
            path=str(audio_file_path),
            media_type="audio/ogg",
            filename=f"chunk_{seq:03d}.ogg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream audio chunk: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 