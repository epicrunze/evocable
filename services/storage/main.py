"""FastAPI application for Audiobook Server Storage Service."""

import os
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy import text
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Audiobook Storage Service",
    description="Centralized storage and metadata management",
    version="1.0.0",
)

# Pydantic models for request/response
class TextData(BaseModel):
    text: str

class ChunkData(BaseModel):
    seq: int
    text: str
    ssml: str
    char_count: int

class ChunksData(BaseModel):
    chunks: list[ChunkData]

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///:memory:")
# Only create directories for file-based databases
if not DATABASE_URL.endswith(":memory:"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("/"):
        db_dir = os.path.dirname(db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        # Ensure the directory is writable
        os.chmod(db_dir, 0o755)
        print(f"Database directory created/verified: {db_dir}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Book(Base):
    """Book model for database."""
    __tablename__ = "books"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    format = Column(String)  # pdf, epub, txt
    status = Column(String)  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Chunk(Base):
    """Audio chunk model for database."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(String, index=True)
    sequence = Column(Integer)
    duration = Column(Integer)  # in milliseconds
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    try:
        # Check database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check file system paths
    paths = {
        "text": os.getenv("TEXT_DATA_PATH", "/data/text"),
        "wav": os.getenv("WAV_DATA_PATH", "/data/wav"),
        "ogg": os.getenv("SEGMENT_DATA_PATH", "/data/ogg"),
    }
    
    path_status = {}
    for name, path in paths.items():
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            path_status[name] = "healthy"
        except Exception as e:
            path_status[name] = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "storage",
        "database": db_status,
        "paths": path_status,
        "version": "1.0.0"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with service information."""
    return {
        "message": "Audiobook Storage Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/books/{book_id}/text")
async def store_book_text(book_id: str, text_data: TextData) -> Dict[str, str]:
    """Store extracted text for a book."""
    try:
        text_path = Path(os.getenv("TEXT_DATA_PATH", "/data/text"))
        text_path.mkdir(parents=True, exist_ok=True)
        
        # Store text to file
        book_text_file = text_path / f"{book_id}.txt"
        with open(book_text_file, 'w', encoding='utf-8') as f:
            f.write(text_data.text)
        
        # Update book status in database
        db = SessionLocal()
        try:
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.status = "text_extracted"
                db.commit()
        finally:
            db.close()
        
        return {"message": f"Text stored for book {book_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store text: {str(e)}")


@app.get("/books/{book_id}/text")
async def get_book_text(book_id: str) -> Dict[str, str]:
    """Get extracted text for a book."""
    try:
        text_path = Path(os.getenv("TEXT_DATA_PATH", "/data/text"))
        book_text_file = text_path / f"{book_id}.txt"
        
        if not book_text_file.exists():
            raise HTTPException(status_code=404, detail=f"Text not found for book {book_id}")
        
        with open(book_text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get text: {str(e)}")


@app.post("/books/{book_id}/chunks")
async def store_book_chunks(book_id: str, chunks_data: ChunksData) -> Dict[str, str]:
    """Store SSML chunks for a book."""
    try:
        text_path = Path(os.getenv("TEXT_DATA_PATH", "/data/text"))
        text_path.mkdir(parents=True, exist_ok=True)
        
        # Create book-specific directory for chunks
        book_chunks_dir = text_path / book_id / "chunks"
        book_chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Store each chunk as a separate SSML file
        for chunk in chunks_data.chunks:
            chunk_file = book_chunks_dir / f"chunk_{chunk.seq:03d}.ssml"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                f.write(chunk.ssml)
            
            # Also store metadata
            metadata_file = book_chunks_dir / f"chunk_{chunk.seq:03d}.json"
            import json
            metadata = {
                "seq": chunk.seq,
                "text": chunk.text,
                "char_count": chunk.char_count,
                "ssml_path": str(chunk_file)
            }
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        
        return {"message": f"Stored {len(chunks_data.chunks)} chunks for book {book_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store chunks: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("STORAGE_HOST", "0.0.0.0"),
        port=int(os.getenv("STORAGE_PORT", "8001")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 