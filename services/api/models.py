"""Data models and schemas for the Audiobook API service."""

import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import sqlite3
from pathlib import Path


class BookFormat(str, Enum):
    """Supported book formats."""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"


class BookStatus(str, Enum):
    """Book processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    SEGMENTING = "segmenting"
    GENERATING_AUDIO = "generating_audio"
    TRANSCODING = "transcoding"
    COMPLETED = "completed"
    FAILED = "failed"


# Pydantic Models for API
class BookSubmissionRequest(BaseModel):
    """Request model for book submission."""
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Book title",
        example="The Great Gatsby"
    )
    format: BookFormat = Field(
        ..., 
        description="Book format (pdf, epub, txt)",
        example=BookFormat.PDF
    )
    # Note: file will be handled separately via multipart/form-data
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "The Great Gatsby",
                    "format": "pdf"
                },
                {
                    "title": "Pride and Prejudice", 
                    "format": "epub"
                },
                {
                    "title": "Alice's Adventures in Wonderland",
                    "format": "txt"
                }
            ]
        }
    }


class BookResponse(BaseModel):
    """Response model for book submission."""
    book_id: str = Field(
        ..., 
        description="Unique book identifier (UUID)",
        example="550e8400-e29b-41d4-a716-446655440000"
    )
    status: BookStatus = Field(
        ..., 
        description="Current processing status", 
        example=BookStatus.PENDING
    )
    message: str = Field(
        default="Book submitted successfully", 
        description="Status message",
        example="Book 'The Great Gatsby' submitted successfully for processing"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "book_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "pending",
                    "message": "Book 'The Great Gatsby' submitted successfully for processing"
                },
                {
                    "book_id": "661f8511-f30c-52e5-b827-557766551001", 
                    "status": "processing",
                    "message": "Book 'Pride and Prejudice' is being processed"
                }
            ]
        }
    }


class BookStatusResponse(BaseModel):
    """Response model for book status check."""
    book_id: str = Field(..., description="Unique book identifier")
    title: str = Field(..., description="Book title")
    status: BookStatus = Field(..., description="Current processing status")
    percent_complete: float = Field(default=0.0, ge=0.0, le=100.0, description="Processing progress percentage")
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")
    created_at: datetime = Field(..., description="Book creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    total_chunks: Optional[int] = Field(default=None, description="Total number of audio chunks")


class ChunkInfo(BaseModel):
    """Information about an audio chunk."""
    seq: int = Field(..., ge=0, description="Chunk sequence number")
    duration_s: float = Field(..., gt=0.0, description="Chunk duration in seconds")
    url: str = Field(..., description="URL to fetch the chunk")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")


class ChunkListResponse(BaseModel):
    """Response model for listing book chunks."""
    book_id: str = Field(..., description="Unique book identifier")
    total_chunks: int = Field(..., ge=0, description="Total number of chunks")
    total_duration_s: float = Field(..., ge=0.0, description="Total audio duration in seconds")
    chunks: List[ChunkInfo] = Field(..., description="List of available chunks")


class BatchSignedUrlRequest(BaseModel):
    """Request model for generating multiple signed URLs."""
    chunks: List[int] = Field(
        ..., 
        description="List of chunk sequence numbers to generate URLs for",
        min_items=1,
        max_items=20,
        example=[0, 1, 2, 3, 4]
    )
    
    @validator('chunks')
    def validate_chunks(cls, v):
        """Validate chunk sequence numbers."""
        for chunk_seq in v:
            if chunk_seq < 0:
                raise ValueError(f"Chunk sequence must be non-negative, got {chunk_seq}")
        return v


class BatchSignedUrlResponse(BaseModel):
    """Response model for batch signed URL generation."""
    book_id: str = Field(..., description="Unique book identifier")
    signed_urls: dict = Field(..., description="Mapping of chunk sequence to signed URL")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    total_chunks: int = Field(..., description="Number of URLs generated")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional error details")


# Database Models
class DatabaseManager:
    """SQLite database manager for audiobook metadata."""
    
    def __init__(self, db_path: str = None):
        # Use environment variable - require it to be explicitly set unless overridden
        if db_path is None:
            db_path = os.getenv("DATABASE_URL")
            if db_path is None:
                raise RuntimeError("DATABASE_URL environment variable is required but not set. Please check your .env file or environment configuration.")
            if db_path.startswith("sqlite:///"):
                db_path = db_path.replace("sqlite:///", "")
                if db_path == ":memory:":
                    db_path = ":memory:"
                else:
                    # Ensure directory exists for file-based databases
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        # For in-memory databases, no directory creation needed
        if self.db_path != ":memory:":
            # Ensure directory exists for file-based databases
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    format TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    percent_complete REAL DEFAULT 0.0,
                    error_message TEXT,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_chunks INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    duration_s REAL NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
                    UNIQUE (book_id, seq)
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_status ON books (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks (book_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_seq ON chunks (book_id, seq)")
            
            conn.commit()
    
    def create_book(self, title: str, format: str, file_path: str) -> str:
        """Create a new book record and return the book ID."""
        book_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            conn.execute("""
                INSERT INTO books (id, title, format, file_path)
                VALUES (?, ?, ?, ?)
            """, (book_id, title, format, file_path))
            conn.commit()
        
        return book_id
    
    def get_book(self, book_id: str) -> Optional[dict]:
        """Get book information by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM books WHERE id = ?
            """, (book_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_books(self) -> List[dict]:
        """Get all books in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM books ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_book_status(self, book_id: str, status: str, percent_complete: Optional[float] = None, 
                          error_message: Optional[str] = None, total_chunks: Optional[int] = None):
        """Update book processing status."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]
            
            if percent_complete is not None:
                updates.append("percent_complete = ?")
                params.append(str(percent_complete))
            
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if total_chunks is not None:
                updates.append("total_chunks = ?")
                params.append(str(total_chunks))
            
            params.append(book_id)
            
            conn.execute(f"""
                UPDATE books SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
    
    def create_chunk(self, book_id: str, seq: int, duration_s: float, 
                    file_path: str, file_size: Optional[int] = None) -> int:
        """Create a new chunk record and return the chunk ID."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            cursor = conn.execute("""
                INSERT INTO chunks (book_id, seq, duration_s, file_path, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, seq, duration_s, file_path, file_size))
            conn.commit()
            result = cursor.lastrowid
            return result if result is not None else 0
    
    def get_chunks(self, book_id: str) -> List[dict]:
        """Get all chunks for a book, ordered by sequence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM chunks 
                WHERE book_id = ? 
                ORDER BY seq
            """, (book_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_chunk(self, book_id: str, seq: int) -> Optional[dict]:
        """Get a specific chunk by book ID and sequence number."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM chunks 
                WHERE book_id = ? AND seq = ?
            """, (book_id, seq))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_book(self, book_id: str):
        """Delete a book and all its chunks."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Delete chunks first (in case cascade doesn't work)
            conn.execute("DELETE FROM chunks WHERE book_id = ?", (book_id,))
            
            # Delete the book
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit() 