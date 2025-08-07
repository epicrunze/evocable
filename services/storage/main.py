"""FastAPI application for Audiobook Server Storage Service."""

import os
import uuid
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import shared database models
from database_models import Base, User, Book, AudioChunk
from datetime import datetime
from sqlalchemy import text
from pydantic import BaseModel

# Import user service and models
from user_service import UserService, UserCreateRequest, UserUpdateRequest, UserResponse

# Import book service and models
from book_service import BookService, BookCreateRequest, BookUpdateRequest, BookResponse, BookListResponse

# Import environment validation
from env_validation import get_required_env, validate_critical_env_vars

# Initialize FastAPI app
app = FastAPI(
    title="Audiobook Storage Service",
    description="Centralized storage and metadata management",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and start user queue processing on application startup."""
    import asyncio
    
    # Initialize database
    init_database()
    
    # Start user queue processing in background
    from user_queue_processor import start_user_queue_processing
    asyncio.create_task(start_user_queue_processing())

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

class AudioChunkData(BaseModel):
    seq: int
    duration_s: float
    file_path: str
    file_size: int
    format: str = "opus"
    container: str = "ogg"
    bitrate: str = "32k"

class AudioChunksData(BaseModel):
    chunks: list[AudioChunkData]

# Validate critical environment variables at startup
validate_critical_env_vars()

# Database setup - require DATABASE_URL to be explicitly set
DATABASE_URL = get_required_env("DATABASE_URL", "SQLite database connection string")

# Only create directories for file-based databases
if not DATABASE_URL.endswith(":memory:"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("/"):
        db_dir = os.path.dirname(db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        # Ensure the directory is writable
        os.chmod(db_dir, 0o755)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Database models are now imported from database_models.py


# Book and Chunk models are now imported from database_models.py

# AudioChunk model is now imported from database_models.py as AudioChunk


def init_database():
    """Initialize database tables and default data."""
    try:
        # Ensure all models are imported and registered with Base
        # Import all models explicitly to register them with Base.metadata
        from database_models import User, Book, AudioChunk
        
        print(f"DEBUG: Registered tables: {list(Base.metadata.tables.keys())}")
        
        # Create tables with error handling
        Base.metadata.create_all(bind=engine)
        print("DEBUG: Database tables created")
        
        # Verify tables were actually created
        from sqlalchemy import text
        print(f"DEBUG: Database URL: {DATABASE_URL}")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            actual_tables = [row[0] for row in result]
            print(f"DEBUG: Actual tables in database: {actual_tables}")
            
            # Also check if we can see users table schema
            if 'users' in actual_tables:
                users_schema = connection.execute(text("SELECT sql FROM sqlite_master WHERE name='users';"))
                print(f"DEBUG: Users table schema: {users_schema.fetchone()}")
            else:
                print("DEBUG: Users table not found in actual database!")
        
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Create default admin user
    create_default_admin_user()


def create_default_admin_user():
    """Create a default admin user if none exists."""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Get admin password from environment or use default
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123!")
            password_hash = pwd_context.hash(admin_password)
            
            # Create default admin user
            admin_user = User(
                id="00000000-0000-0000-0000-000000000001",  # Fixed UUID for admin
                username="admin",
                email="admin@example.com",  # Changed to valid domain
                password_hash=password_hash,
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print("✅ Created default admin user (admin@example.com)")  # Updated message
            if admin_password == "admin123!":
                print("⚠️ Using default admin password - set ADMIN_PASSWORD environment variable for production")
        else:
            print("ℹ️ Admin user already exists")
    except Exception as e:
        print(f"⚠️ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


# Database initialization will be called during FastAPI startup


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


@app.post("/books/{book_id}/audio-chunks")
async def store_audio_chunks(book_id: str, audio_chunks_data: AudioChunksData) -> Dict[str, str]:
    """Store streaming audio chunk metadata for a book."""
    try:
        # Store chunk metadata in database
        db = SessionLocal()
        try:
            # Clear existing chunks for this book
            db.query(Chunk).filter(Chunk.book_id == book_id).delete()
            
            # Add new chunks
            for chunk_data in audio_chunks_data.chunks:
                chunk = Chunk(
                    book_id=book_id,
                    sequence=chunk_data.seq,
                    duration=int(chunk_data.duration_s * 1000),  # Convert to milliseconds
                    file_path=chunk_data.file_path
                )
                db.add(chunk)
            
            db.commit()
            
            # Update book status
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                book.status = "completed"
                db.commit()
                
        finally:
            db.close()
        
        return {"message": f"Stored {len(audio_chunks_data.chunks)} audio chunks for book {book_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store audio chunks: {str(e)}")


@app.get("/books/{book_id}/audio-chunks")
async def get_audio_chunks(book_id: str) -> Dict[str, Any]:
    """Get streaming audio chunks for a book."""
    try:
        db = SessionLocal()
        try:
            chunks = db.query(Chunk).filter(Chunk.book_id == book_id).order_by(Chunk.sequence).all()
            
            chunk_list = []
            total_duration = 0.0
            
            for chunk in chunks:
                duration_s = chunk.duration / 1000.0  # Convert from milliseconds
                chunk_info = {
                    "seq": chunk.sequence,
                    "duration_s": duration_s,
                    "file_path": chunk.file_path,
                    "url": f"/books/{book_id}/chunks/{chunk.sequence}"
                }
                chunk_list.append(chunk_info)
                total_duration += duration_s
            
            return {
                "book_id": book_id,
                "total_chunks": len(chunk_list),
                "total_duration_s": total_duration,
                "chunks": chunk_list
            }
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audio chunks: {str(e)}")


@app.get("/books/{book_id}/wav-files")
async def get_wav_files(book_id: str) -> Dict[str, Any]:
    """Get WAV files for a book from the file system."""
    try:
        wav_path = Path(os.getenv("WAV_DATA_PATH", "/data/wav"))
        book_wav_dir = wav_path / book_id
        
        if not book_wav_dir.exists():
            raise HTTPException(status_code=404, detail=f"WAV files not found for book {book_id}")
        
        # Check for metadata file
        metadata_file = book_wav_dir / "metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail=f"WAV metadata not found for book {book_id}")
        
        # Read metadata
        import json
        with open(metadata_file, 'r') as f:
            wav_files = json.load(f)
        
        return {
            "book_id": book_id,
            "wav_files": wav_files,
            "total_files": len(wav_files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WAV files: {str(e)}")


@app.delete("/books/{book_id}/audio-chunks")
async def delete_audio_chunks(book_id: str) -> Dict[str, str]:
    """Delete all audio chunks for a book."""
    try:
        db = SessionLocal()
        try:
            # Delete chunks from database
            deleted_count = db.query(Chunk).filter(Chunk.book_id == book_id).delete()
            
            # Delete book record if it exists
            book_deleted = db.query(Book).filter(Book.id == book_id).delete()
            
            db.commit()
            
            return {
                "message": f"Deleted {deleted_count} chunks and {book_deleted} book record for book {book_id}"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete audio chunks: {str(e)}")


# User Management Endpoints

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreateRequest) -> UserResponse:
    """Create a new user account."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_response = await user_service.create_user(user_data)
        return user_response
        
    except ValueError as e:
        # Handle validation errors from user service
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail=f"Failed to create user: {str(e)}")
    finally:
        db.close()


@app.post("/users/authenticate")
async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user with email and password."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        authenticated_user = await user_service.authenticate_user(email, password)
        
        if authenticated_user:
            return {
                "success": True,
                "user": {
                    "id": authenticated_user.id,
                    "username": authenticated_user.username,
                    "email": authenticated_user.email,
                    "is_active": authenticated_user.is_active,
                    "is_verified": authenticated_user.is_verified
                }
            }
        else:
            return {"success": False, "user": None}
            
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Authentication failed: {str(e)}")
    finally:
        db.close()


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str) -> UserResponse:
    """Get user by ID."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_response = await user_service.get_user_by_id(user_id)
        
        if not user_response:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return user_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to get user: {str(e)}")
    finally:
        db.close()


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, update_data: UserUpdateRequest) -> UserResponse:
    """Update user profile."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(user_id, update_data)
        
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return updated_user
        
    except ValueError as e:
        # Handle validation errors (duplicate username/email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to update user: {str(e)}")
    finally:
        db.close()


@app.post("/users/{user_id}/change-password")
async def change_user_password(user_id: str, current_password: str, new_password: str) -> Dict[str, str]:
    """Change user password."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        success = await user_service.change_password(user_id, current_password, new_password)
        
        if success:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                              detail="Current password is incorrect")
        
    except ValueError as e:
        # Password validation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to change password: {str(e)}")
    finally:
        db.close()


@app.post("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str) -> Dict[str, str]:
    """Deactivate user account."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        success = await user_service.deactivate_user(user_id)
        
        if success:
            return {"message": "User deactivated successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to deactivate user: {str(e)}")
    finally:
        db.close()


@app.post("/users/{user_id}/activate")
async def activate_user(user_id: str) -> Dict[str, str]:
    """Activate user account."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        success = await user_service.activate_user(user_id)
        
        if success:
            return {"message": "User activated successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to activate user: {str(e)}")
    finally:
        db.close()


@app.get("/users", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, active_only: bool = True) -> List[UserResponse]:
    """List users with pagination."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        users = await user_service.list_users(skip=skip, limit=limit, active_only=active_only)
        return users
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to list users: {str(e)}")
    finally:
        db.close()


@app.get("/users/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str) -> UserResponse:
    """Get user by email address."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_db = await user_service.get_user_by_email(email)
        
        if not user_db:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                              detail="User not found")
        
        return UserResponse.from_orm(user_db)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.post("/users/reset-password")
async def reset_password_by_email(email: str, new_password: str):
    """Reset password for user with given email."""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        success = await user_service.reset_password_by_email(email, new_password)
        
        if success:
            return {"success": True, "message": "Password reset successfully"}
        else:
            return {"success": False, "message": "User not found"}
            
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Failed to reset password: {str(e)}")
    finally:
        db.close()


# === BOOK MANAGEMENT ENDPOINTS ===

@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book_data: BookCreateRequest) -> BookResponse:
    """Create a new book."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_response = await book_service.create_book(book_data)
        return book_response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.get("/books", response_model=BookListResponse)
async def list_books(
    user_id: str = Query(None, description="Filter books by user ID"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page")
) -> BookListResponse:
    """List books with optional user filtering and pagination."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        books_response = await book_service.list_books(user_id=user_id, page=page, per_page=per_page)
        return books_response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    user_id: str = Query(None, description="Filter by user ownership")
) -> BookResponse:
    """Get book by ID with optional user ownership check."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = await book_service.get_book_by_id(book_id, user_id=user_id)
        if not book:
            if user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found or access denied")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found")
        return book
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: str,
    book_data: BookUpdateRequest,
    user_id: str = Query(None, description="Ensure user ownership")
) -> BookResponse:
    """Update book information with optional ownership check."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = await book_service.update_book(book_id, book_data, user_id=user_id)
        if not book:
            if user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found or access denied")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found")
        return book
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.put("/books/{book_id}/status")
async def update_book_status(
    book_id: str,
    status: str = Query(..., description="New book status"),
    user_id: str = Query(None, description="Ensure user ownership")
) -> BookResponse:
    """Update book processing status with optional ownership check."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = await book_service.update_book_status(book_id, status, user_id=user_id)
        if not book:
            if user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found or access denied")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found")
        return book
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


@app.delete("/books/{book_id}")
async def delete_book(
    book_id: str,
    user_id: str = Query(None, description="Ensure user ownership")
):
    """Delete a book with optional ownership check."""
    db = SessionLocal()
    try:
        book_service = BookService(db)
        success = await book_service.delete_book(book_id, user_id=user_id)
        if not success:
            if user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found or access denied")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                  detail="Book not found")
        return {"message": f"Book {book_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("STORAGE_HOST", "0.0.0.0"),
        port=int(os.getenv("STORAGE_PORT", "8001")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 