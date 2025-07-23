"""FastAPI application for Audiobook Server API Gateway."""

print("MAIN.PY TOP LEVEL EXECUTED - UNIQUE TEST PRINT")

import os
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import hmac
import hashlib
import time
from urllib.parse import urlencode

print("DEBUG: Basic imports completed")

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile, BackgroundTasks, Query, Request, Path
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

# Import authentication models
from auth_models import (
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    LogoutResponse,
    User,
    session_manager
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

print("DEBUG: About to initialize FastAPI app")
# Initialize FastAPI app
app = FastAPI(
    title="Audiobook Server API",
    description="""
# 🎵 Audiobook Server API

Convert PDF, EPUB, and TXT files into high-quality streaming audiobooks with this comprehensive API.

## 🚀 Features

- **Multi-format Support**: Process PDF, EPUB, and TXT files
- **AI-Powered Processing**: Advanced text extraction and segmentation
- **High-Quality Audio**: TTS generation with Opus encoding at 32kbps
- **Streaming Ready**: Audio chunks optimized for web streaming
- **Real-time Progress**: Monitor processing status with live updates
- **Secure Access**: API key and session-based authentication
- **Production Ready**: Rate limiting, caching, and error handling

## 📊 Processing Pipeline

1. **Upload** → File validation and storage
2. **Extract** → Text extraction from various formats
3. **Segment** → Intelligent text chunking for optimal audio
4. **Generate** → High-quality TTS audio generation
5. **Transcode** → Opus encoding for web streaming
6. **Stream** → Chunked audio delivery

## 🔧 Audio Specifications

- **Codec**: Opus in Ogg container
- **Bitrate**: 32 kbps (optimized for voice)
- **Chunk Duration**: ~3.14 seconds
- **Sample Rate**: 22050 Hz
- **Format**: Streaming-optimized segments

## 🛡️ Authentication

All endpoints require authentication via Bearer token:
- **API Key**: For service-to-service communication
- **Session Token**: For user sessions (obtained via /auth/login)

## 📈 Rate Limits

- **General API**: 60 requests/minute
- **File Uploads**: 10 requests/minute  
- **Audio Streaming**: 300 requests/minute

## 📝 Usage Examples

### Quick Start
```bash
# 1. Submit a book
curl -X POST "http://server.epicrunze.com/api/v1/books" \\
  -H "Authorization: Bearer your-api-key" \\
  -F "title=My Book" \\
  -F "format=pdf" \\
  -F "file=@book.pdf"

# 2. Check processing status
curl -H "Authorization: Bearer your-api-key" \\
  http://server.epicrunze.com/api/v1/books/{book_id}/status

# 3. List audio chunks when ready
curl -H "Authorization: Bearer your-api-key" \\
  http://server.epicrunze.com/api/v1/books/{book_id}/chunks

# 4. Stream audio chunk
curl -H "Authorization: Bearer your-api-key" \\
  http://server.epicrunze.com/api/v1/books/{book_id}/chunks/0
```

For detailed examples and integration guides, see the individual endpoint documentation below.
    """,
    version="1.0.0",
    contact={
        "name": "Audiobook Server API Support",
        "url": "https://server.epicrunze.com",
        "email": "support@epicrunze.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://server.epicrunze.com",
            "description": "Production server"
        },
        {
            "url": "http://localhost",
            "description": "Local development server"
        }
    ],
    tags_metadata=[
        {
            "name": "Health",
            "description": "Service health and status monitoring"
        },
        {
            "name": "Authentication", 
            "description": "User authentication and session management"
        },
        {
            "name": "Books",
            "description": "Book management and processing operations"
        },
        {
            "name": "Audio",
            "description": "Audio chunk streaming and playback"
        },
        {
            "name": "Legacy",
            "description": "Legacy endpoints for backward compatibility"
        }
    ],
    lifespan=lifespan
)
print("DEBUG: FastAPI app initialized successfully")

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_credentials=False if allow_all_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
print("DEBUG: About to create Redis client")
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)
print("DEBUG: Redis client created successfully")

# HTTP client for service communication
print("DEBUG: About to create HTTP client")
http_client = httpx.AsyncClient()
print("DEBUG: HTTP client created successfully")

# Database manager
print("DEBUG: About to create DatabaseManager")
db_manager = DatabaseManager(
    db_path=os.getenv("DATABASE_PATH", "/data/meta/audiobooks.db")
)
print("DEBUG: DatabaseManager created successfully")


def verify_authentication(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify authentication from Authorization header (API key or session token)."""
    token = credentials.credentials
    
    # First, try to validate as session token
    payload = session_manager.validate_session_token(token)
    if payload:
        return token
    
    # If not a valid session token, try as API key
    if session_manager.validate_api_key(token):
        return token
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )

print("DEBUG: verify_authentication function defined")


def get_optional_credentials(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Get optional Authorization header credentials."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return None

print("DEBUG: get_optional_credentials function defined")

def verify_authentication_query(
    request: Request = Depends(),
    query_token: str = Query(None, alias="token")
) -> str:
    """Verify authentication from Authorization header OR query parameter."""
    print("[AUTH DEBUG] ===== FUNCTION CALLED =====")
    print("[AUTH DEBUG] Incoming request headers:", dict(request.headers))
    print("[AUTH DEBUG] Query token:", query_token)
    # Try Authorization header first
    credentials = get_optional_credentials(request)
    if credentials:
        token = credentials.credentials
        print("[AUTH DEBUG] Found Authorization header token:", token)
        try:
            payload = session_manager.validate_session_token(token)
            print("[AUTH DEBUG] Session token payload:", payload)
            if payload:
                print("[AUTH DEBUG] Authenticated via session token (header)")
                return token
            if session_manager.validate_api_key(token):
                print("[AUTH DEBUG] Authenticated via API key (header)")
                return token
        except Exception as e:
            print("[AUTH DEBUG] Exception during header token validation:", e)
    else:
        print("[AUTH DEBUG] No Authorization header present")
    # Try query parameter
    if query_token:
        print("[AUTH DEBUG] Trying query token:", query_token)
        try:
            payload = session_manager.validate_session_token(query_token)
            print("[AUTH DEBUG] Session token payload (query):", payload)
            if payload:
                print("[AUTH DEBUG] Authenticated via session token (query)")
                return query_token
            if session_manager.validate_api_key(query_token):
                print("[AUTH DEBUG] Authenticated via API key (query)")
                return query_token
        except Exception as e:
            print("[AUTH DEBUG] Exception during query token validation:", e)
    else:
        print("[AUTH DEBUG] No query token present")
    print("[AUTH DEBUG] Authentication failed")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )

print("DEBUG: verify_authentication_query function defined")

print("DEBUG: Defining generate_signed_url function")
def generate_signed_url(book_id: str, chunk_seq: int, token: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for audio chunk access."""
    print("DEBUG: generate_signed_url function called")
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    endpoint = f"/api/v1/books/{book_id}/chunks/{chunk_seq}"
    
    # Create signature payload
    timestamp = int(time.time())
    expires_at = timestamp + expires_in
    
    # Create signature string
    signature_data = f"{endpoint}:{expires_at}:{token}"
    signature = hmac.new(
        session_manager.secret_key.encode(),
        signature_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Build signed URL
    params = {
        "expires": expires_at,
        "signature": signature,
        "token": token
    }
    
    return f"{base_url}{endpoint}?{urlencode(params)}"

print("DEBUG: generate_signed_url function defined")

def verify_signed_url(request: Request, book_id: str, chunk_seq: int) -> str:
    """Verify a signed URL and return the authenticated token."""
    expires = request.query_params.get("expires")
    signature = request.query_params.get("signature")
    token = request.query_params.get("token")
    
    if not all([expires, signature, token]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signed URL parameters"
        )
    
    # Check expiration
    current_time = int(time.time())
    if current_time > int(expires):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signed URL has expired"
        )
    
    # Verify signature
    endpoint = f"/api/v1/books/{book_id}/chunks/{chunk_seq}"
    signature_data = f"{endpoint}:{expires}:{token}"
    expected_signature = hmac.new(
        session_manager.secret_key.encode(),
        signature_data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Validate token
    payload = session_manager.validate_session_token(token)
    if payload:
        return token
    
    if session_manager.validate_api_key(token):
        return token
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token"
    )

print("DEBUG: verify_signed_url function defined")

@app.get(
    "/health",
    tags=["Health"],
    summary="Check service health",
    description="""
    Comprehensive health check for all system components.
    
    This endpoint monitors:
    - **API Service**: Core application status
    - **Redis**: Message queue and caching system  
    - **Database**: SQLite metadata storage
    - **Pipeline**: Background processing services
    
    Use this endpoint for:
    - Load balancer health checks
    - Monitoring and alerting systems
    - System diagnostics and troubleshooting
    
    **No authentication required** - public health endpoint.
    """,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "api",
                        "redis": "healthy",
                        "database": "healthy", 
                        "pipeline": {
                            "redis": "healthy",
                            "database": "healthy",
                            "pipeline": "ready"
                        },
                        "version": "1.0.0"
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "service": "api",
                        "redis": "unhealthy: Connection refused",
                        "database": "healthy",
                        "pipeline": "unhealthy",
                        "version": "1.0.0"
                    }
                }
            }
        }
    }
)
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


@app.post("/test")
async def test_post(data: dict = None) -> Dict[str, Any]:
    """Test POST endpoint to debug frontend requests."""
    return {
        "message": "POST request successful",
        "received_data": data,
        "method": "POST"
    }


@app.get("/test-route")
async def test_route():
    return {"message": "Test route is working"}


# Authentication endpoints
@app.post(
    "/auth/login", 
    response_model=LoginResponse,
    tags=["Authentication"],
    summary="Authenticate and get session token",
    description="""
    Exchange an API key for a session token with optional "remember me" functionality.
    
    ## Usage
    
    Use this endpoint to:
    - Convert API keys to session tokens for web applications
    - Enable temporary authentication without exposing API keys
    - Support "remember me" functionality for extended sessions
    
    ## Token Types
    
    - **Standard Session**: Expires in 1 hour
    - **Remember Me Session**: Expires in 30 days
    
    ## Security Notes
    
    - Session tokens are JWT-based and contain user information
    - Tokens are signed with a server secret key
    - Use HTTPS in production to protect tokens in transit
    """,
    responses={
        200: {
            "description": "Authentication successful",
            "content": {
                "application/json": {
                    "example": {
                        "sessionToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "expiresAt": "2024-12-31T23:59:59Z",
                        "user": {
                            "id": "admin",
                            "username": "admin",
                            "role": "administrator"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key"
                    }
                }
            }
        },
        422: {
            "description": "Invalid request format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "apiKey"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate user with API key and return session token."""
    try:
        if not session_manager.validate_api_key(request.apiKey):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Create session token
        user_id = "admin"  # For now, single admin user
        session_token, expires_at = session_manager.create_session_token(
            user_id, 
            remember=request.remember or False
        )
        
        # Get user info
        user = session_manager.get_user_info(user_id)
        
        return LoginResponse(
            sessionToken=session_token,
            expiresAt=expires_at.isoformat() + "Z",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_token(token: str = Depends(verify_authentication)) -> RefreshResponse:
    """Refresh session token."""
    try:
        result = session_manager.refresh_session_token(token)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        new_token, expires_at, user = result
        
        return RefreshResponse(
            sessionToken=new_token,
            expiresAt=expires_at.isoformat() + "Z",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@app.post("/auth/logout", response_model=LogoutResponse)
async def logout(token: str = Depends(verify_authentication)) -> LogoutResponse:
    """Logout user and invalidate session token."""
    try:
        # For now, just return success message
        # In production, you might want to maintain a blacklist of invalidated tokens
        return LogoutResponse(
            message="Successfully logged out"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


# Book management endpoints

@app.get(
    "/api/v1/books",
    tags=["Books"],
    summary="List all books",
    description="""
    Retrieve a list of all books in the system with their current processing status.
    
    ## Response Information
    
    Each book includes:
    - **Basic Info**: ID, title, format, creation/update timestamps
    - **Processing Status**: Current stage and completion percentage
    - **Metadata**: Total chunks available (if processing complete)
    - **Error Details**: Error messages if processing failed
    
    ## Book Statuses
    
    - `pending` - Book uploaded, awaiting processing
    - `extracting` - Text extraction in progress
    - `segmenting` - Text chunking and preparation
    - `generating_audio` - TTS audio generation
    - `transcoding` - Audio encoding to Opus format
    - `completed` - Ready for streaming
    - `failed` - Processing error occurred
    
    ## Use Cases
    
    - Display book library in web interface
    - Monitor processing progress across all books
    - Validate API authentication (returns 401 if invalid)
    """,
    responses={
        200: {
            "description": "List of books retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "books": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "title": "The Great Gatsby",
                                "format": "pdf",
                                "status": "completed",
                                "percent_complete": 100.0,
                                "error_message": None,
                                "file_path": "/data/text/550e8400-e29b-41d4-a716-446655440000/gatsby.pdf",
                                "created_at": "2024-01-15T10:30:00",
                                "updated_at": "2024-01-15T10:45:00",
                                "total_chunks": 42
                            },
                            {
                                "id": "661f8511-f30c-52e5-b827-557766551001",
                                "title": "Pride and Prejudice", 
                                "format": "epub",
                                "status": "generating_audio",
                                "percent_complete": 65.0,
                                "error_message": None,
                                "file_path": "/data/text/661f8511-f30c-52e5-b827-557766551001/pride.epub",
                                "created_at": "2024-01-15T11:00:00",
                                "updated_at": "2024-01-15T11:15:00",
                                "total_chunks": None
                            }
                        ]
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid authentication credentials"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to list books: Database connection error"
                    }
                }
            }
        }
    }
)
async def list_books(token: str = Depends(verify_authentication)):
    """List all books - used for authentication validation."""
    try:
        books = db_manager.list_books()
        return {"books": books}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list books: {str(e)}"
        )


@app.post(
    "/api/v1/books", 
    response_model=BookResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["Books"],
    summary="Upload and process book",
    description="""
    Upload a book file and start the automated processing pipeline to convert it into a streaming audiobook.
    
    ## Supported Formats
    
    - **PDF**: Text-based PDFs with embedded text (not scanned images)
    - **EPUB**: Standard EPUB format with HTML/XHTML content
    - **TXT**: Plain text files with UTF-8 encoding
    
    ## File Requirements
    
    - **Maximum Size**: 50 MB per file
    - **File Extension**: Must match the specified format
    - **Content**: Must contain readable text content
    
    ## Processing Pipeline
    
    After upload, your book goes through these stages:
    
    1. **Upload Validation** (Immediate)
    2. **Text Extraction** (~1-3 minutes)
    3. **Text Segmentation** (~30 seconds) 
    4. **Audio Generation** (~2-10 minutes depending on length)
    5. **Audio Transcoding** (~1-2 minutes)
    
    ## Typical Processing Times
    
    - **Small book** (<10 pages): 2-5 minutes
    - **Medium book** (10-50 pages): 5-15 minutes  
    - **Large book** (>50 pages): 15+ minutes
    
    ## Usage Tips
    
    - Use descriptive titles for easy identification
    - Check file format and size before upload
    - Monitor progress using the status endpoint
    - Books are processed asynchronously - no need to wait
    """,
    responses={
        201: {
            "description": "Book uploaded successfully and processing started",
            "content": {
                "application/json": {
                    "example": {
                        "book_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "pending",
                        "message": "Book 'The Great Gatsby' submitted successfully for processing"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request - format mismatch, missing file, etc.",
            "content": {
                "application/json": {
                    "examples": {
                        "format_mismatch": {
                            "summary": "File extension doesn't match format",
                            "value": {
                                "detail": "File extension .txt doesn't match format pdf"
                            }
                        },
                        "no_file": {
                            "summary": "No file provided",
                            "value": {
                                "detail": "No file provided"
                            }
                        },
                        "invalid_format": {
                            "summary": "Unsupported format",
                            "value": {
                                "detail": "Invalid format. Supported formats: pdf, epub, txt"
                            }
                        }
                    }
                }
            }
        },
        413: {
            "description": "File too large",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File too large. Maximum size is 50MB"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid authentication credentials"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during processing",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to process book submission: Database connection error"
                    }
                }
            }
        }
    }
)
async def submit_book(
    title: str = Form(..., description="Book title (1-255 characters)", example="The Great Gatsby"),
    format: str = Form(..., description="Book format", example="pdf", regex="^(pdf|epub|txt)$"),
    file: UploadFile = File(..., description="Book file to process (max 50MB)"),
    token: str = Depends(verify_authentication)
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
    token: str = Depends(verify_authentication)
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
        
        # Get total chunks from storage service if completed
        total_chunks = None
        if book["status"] == BookStatus.COMPLETED.value:
            # Get chunks from storage service (same logic as chunks endpoint)
            storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
            print(f"DEBUG STATUS: Getting chunks for {book_id} from {storage_url}")
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{storage_url}/books/{book_id}/audio-chunks")
                    print(f"DEBUG STATUS: Storage response status: {response.status_code}")
                    if response.status_code == 200:
                        storage_data = response.json()
                        total_chunks = storage_data.get("total_chunks", 0)
                        print(f"DEBUG STATUS: Got total_chunks: {total_chunks}")
                    else:
                        print(f"DEBUG STATUS: Storage returned {response.status_code}")
                    # If storage service returns 404, total_chunks remains None (will show as 0)
            except Exception as e:
                # If we can't reach storage service, total_chunks remains None
                print(f"DEBUG STATUS: Exception getting chunks: {e}")
        elif book["total_chunks"] > 0:
            total_chunks = book["total_chunks"]
            print(f"DEBUG STATUS: Using book total_chunks: {total_chunks}")
        
        print(f"DEBUG STATUS: Final total_chunks value: {total_chunks}")
        
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
    token: str = Depends(verify_authentication)
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
        
        # Get chunks from storage service
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{storage_url}/books/{book_id}/audio-chunks")
            
            if response.status_code == 404:
                # No chunks found
                return ChunkListResponse(
                    book_id=book_id,
                    total_chunks=0,
                    total_duration_s=0.0,
                    chunks=[]
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to get chunks from storage service: {response.status_code}"
                )
            
            storage_data = response.json()
            
            # Convert to API response format
            chunks = []
            for chunk_data in storage_data.get("chunks", []):
                chunk_url = f"/api/v1/books/{book_id}/chunks/{chunk_data['seq']}"
                chunk_info = ChunkInfo(
                    seq=chunk_data["seq"],
                    duration_s=chunk_data["duration_s"],
                    url=chunk_url,
                    file_size=chunk_data.get("file_size")
                )
                chunks.append(chunk_info)
            
            return ChunkListResponse(
                book_id=book_id,
                total_chunks=storage_data.get("total_chunks", 0),
                total_duration_s=storage_data.get("total_duration_s", 0.0),
                chunks=chunks
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list book chunks: {str(e)}"
        )


@app.post("/api/v1/books/{book_id}/chunks/{seq}/signed-url")
async def generate_chunk_signed_url(
    book_id: str,
    seq: int,
    expires_in: int = Query(3600, description="URL expiration time in seconds"),
    token: str = Depends(verify_authentication)
) -> Dict[str, Any]:
    """Generate a signed URL for accessing an audio chunk."""
    print(f"DEBUG: Signed URL endpoint called with book_id={book_id}, seq={seq}, expires_in={expires_in}")
    try:
        # Verify book exists
        book = db_manager.get_book(book_id)
        if not book:
            print(f"DEBUG: Book {book_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        print(f"DEBUG: Book {book_id} found, generating signed URL")
        # Generate signed URL
        signed_url = generate_signed_url(book_id, seq, token, expires_in)
        
        print(f"DEBUG: Generated signed URL: {signed_url}")
        return {
            "signed_url": signed_url,
            "expires_in": expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error generating signed URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate signed URL: {str(e)}"
        )


@app.get(
    "/api/v1/books/{book_id}/chunks/{seq}",
    tags=["Audio"],
    summary="Stream audio chunk",
    description="""
    Stream a specific audio chunk from a processed book.
    
    ## Audio Format
    
    - **Codec**: Opus in Ogg container
    - **Bitrate**: 32 kbps (optimized for voice)
    - **Chunk Duration**: ~3.14 seconds per chunk
    - **Sample Rate**: 22050 Hz
    
    ## Authentication Options
    
    This endpoint supports two authentication methods:
    
    1. **Signed URL**: Use signed URLs for secure, temporary access
       - Generated via `/api/v1/books/{book_id}/chunks/{seq}/signed-url`
       - Includes expiration time and signature
       - Ideal for client-side audio players
    
    2. **Authorization Header**: Standard Bearer token authentication
       - Use API key or session token in Authorization header
       - Suitable for server-to-server requests
    
    ## Usage Examples
    
         ### HTML5 Audio Player
     ```html
     <audio controls>
       <source src="http://server.epicrunze.com/api/v1/books/{book_id}/chunks/0?token=your-token" type="audio/ogg">
     </audio>
     ```
     
     ### JavaScript Fetch
     ```javascript
     const response = await fetch(`http://server.epicrunze.com/api/v1/books/{book_id}/chunks/0`, {
       headers: {
         'Authorization': 'Bearer your-token'
       }
     });
     const audioBlob = await response.blob();
     ```
    
    ## Caching
    
    - Audio chunks are cached for 1 hour
    - Use ETag headers for conditional requests
    - Content-Length header provided for progress tracking
    """,
    responses={
        200: {
            "description": "Audio chunk streamed successfully",
            "content": {
                "audio/ogg": {
                    "example": "Binary audio data (Opus in Ogg container)"
                }
            },
            "headers": {
                "Content-Type": {
                    "description": "Always audio/ogg for Opus-encoded chunks"
                },
                "Content-Length": {
                    "description": "Size of the audio chunk in bytes"
                },
                "Cache-Control": {
                    "description": "Caching directives (max-age=3600)"
                },
                "ETag": {
                    "description": "Entity tag for cache validation"
                }
            }
        },
        404: {
            "description": "Book or chunk not found",
            "content": {
                "application/json": {
                    "examples": {
                        "book_not_found": {
                            "summary": "Book doesn't exist",
                            "value": {
                                "detail": "Book with ID 550e8400-e29b-41d4-a716-446655440000 not found"
                            }
                        },
                        "chunk_not_found": {
                            "summary": "Chunk doesn't exist or book not processed",
                            "value": {
                                "detail": "Audio chunk 5 not found for book"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid authentication token",
                            "value": {
                                "detail": "Invalid authentication credentials"
                            }
                        },
                        "expired_signed_url": {
                            "summary": "Signed URL expired",
                            "value": {
                                "detail": "Signed URL has expired"
                            }
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error during streaming",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to stream audio chunk: Storage service unavailable"
                    }
                }
            }
        }
    }
)
async def get_audio_chunk(
    book_id: str = Path(..., description="Unique book identifier", example="550e8400-e29b-41d4-a716-446655440000"), 
    seq: int = Path(..., description="Chunk sequence number (0-based)", example=0, ge=0),
    request: Request = Depends()
):
    """Stream an audio chunk with multiple authentication methods."""
    try:
        # Try signed URL authentication first
        if "signature" in request.query_params:
            token = verify_signed_url(request, book_id, seq)
        else:
            # Fallback to query parameter authentication
            token = verify_authentication_query(request, request.query_params.get("token"))
        
        # Check if book exists
        book = db_manager.get_book(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Get chunk information from storage service
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{storage_url}/books/{book_id}/audio-chunks")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No chunks found for book {book_id}"
                )
            
            storage_data = response.json()
            chunks = storage_data.get("chunks", [])
            
            # Find the specific chunk
            chunk = None
            for chunk_data in chunks:
                if chunk_data["seq"] == seq:
                    chunk = chunk_data
                    break
            
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
                filename=f"chunk_{seq:06d}.ogg"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream audio chunk: {str(e)}"
        )


@app.get("/debug/books/{book_id}/chunks")
async def debug_book_chunks(book_id: str):
    """Debug endpoint to see what's happening with chunks."""
    try:
        print(f"DEBUG: Getting chunks for book {book_id}")
        
        # Check if book exists
        book = db_manager.get_book(book_id)
        print(f"DEBUG: Book found: {book is not None}")
        if not book:
            return {"error": "Book not found"}
        
        # Get chunks from storage service
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        print(f"DEBUG: Storage URL: {storage_url}")
        
        async with httpx.AsyncClient() as client:
            url = f"{storage_url}/books/{book_id}/audio-chunks"
            print(f"DEBUG: Calling URL: {url}")
            
            response = await client.get(url)
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text length: {len(response.text)}")
            
            if response.status_code == 404:
                print("DEBUG: Storage returned 404")
                return {"status": "404", "message": "No chunks found"}
            elif response.status_code != 200:
                print(f"DEBUG: Storage returned error: {response.status_code}")
                return {"status": response.status_code, "error": "Storage service error"}
            
            storage_data = response.json()
            print(f"DEBUG: Storage data keys: {list(storage_data.keys())}")
            print(f"DEBUG: Total chunks from storage: {storage_data.get('total_chunks', 0)}")
            print(f"DEBUG: Chunks array length: {len(storage_data.get('chunks', []))}")
            
            # Convert to API response format
            chunks = []
            for chunk_data in storage_data.get("chunks", []):
                chunk_url = f"/api/v1/books/{book_id}/chunks/{chunk_data['seq']}"
                chunk_info = {
                    "seq": chunk_data["seq"],
                    "duration_s": chunk_data["duration_s"],
                    "url": chunk_url,
                    "file_size": chunk_data.get("file_size")
                }
                chunks.append(chunk_info)
            
            result = {
                "book_id": book_id,
                "total_chunks": storage_data.get("total_chunks", 0),
                "total_duration_s": storage_data.get("total_duration_s", 0.0),
                "chunks": chunks
            }
            
            print(f"DEBUG: Final result total_chunks: {result['total_chunks']}")
            print(f"DEBUG: Final result chunks length: {len(result['chunks'])}")
            
            return result
        
    except Exception as e:
        print(f"DEBUG: Exception occurred: {str(e)}")
        return {"error": str(e)}


@app.delete("/api/v1/books/{book_id}")
async def delete_book(
    book_id: str,
    token: str = Depends(verify_authentication)
):
    """Delete a book and all its associated data."""
    try:
        # Check if book exists
        book = db_manager.get_book(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Delete from main database
        db_manager.delete_book(book_id)
        
        # Clean up storage service chunks
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        try:
            async with httpx.AsyncClient() as client:
                # Delete chunks from storage database
                await client.delete(f"{storage_url}/books/{book_id}/audio-chunks")
        except Exception as e:
            print(f"Warning: Failed to delete chunks from storage service: {e}")
        
        # Clean up files
        import shutil
        file_paths_to_remove = [
            f"/data/text/{book_id}",
            f"/data/wav/{book_id}",
            f"/data/ogg/{book_id}"
        ]
        
        for path in file_paths_to_remove:
            try:
                if Path(path).exists():
                    shutil.rmtree(path)
                    print(f"Deleted directory: {path}")
            except Exception as e:
                print(f"Warning: Failed to delete {path}: {e}")
        
        return {"message": f"Successfully deleted book '{book['title']}' and all associated data"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}"
        )


# ============================================================================
# Route aliases for frontend compatibility
# The frontend expects routes at /books/* but our API uses /api/v1/books/*
# ============================================================================

@app.get(
    "/books",
    tags=["Legacy"],
    summary="List books (legacy)",
    description="Legacy endpoint for backward compatibility. Use `/api/v1/books` instead.",
    deprecated=True
)
async def list_books_alias(
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"), 
    token: str = Depends(verify_authentication)
):
    """Alias for /api/v1/books - List all books."""
    return await list_books(token)


@app.post("/books/upload", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def upload_book_alias(
    title: str = Form(..., description="Book title"),
    format: str = Form(..., description="Book format (pdf, epub, txt)"),
    file: UploadFile = File(..., description="Book file to process"),
    token: str = Depends(verify_authentication)
):
    """Alias for /api/v1/books - Upload and process a book."""
    return await submit_book(title, format, file, token)


@app.get("/books/{book_id}")
async def get_book_alias(
    book_id: str,
    token: str = Depends(verify_authentication)
):
    """Alias for /api/v1/books/{book_id}/status - Get book details."""
    return await get_book_status(book_id, token)


@app.delete("/books/{book_id}")
async def delete_book_alias(
    book_id: str,
    token: str = Depends(verify_authentication)
):
    """Alias for /api/v1/books/{book_id} - Delete a book."""
    return await delete_book(book_id, token)


@app.get("/books/{book_id}/chunks")
async def get_book_chunks_alias(
    book_id: str,
    token: str = Depends(verify_authentication)
):
    """Alias for /api/v1/books/{book_id}/chunks - Get book audio chunks."""
    return await list_book_chunks(book_id, token)


@app.post("/books/{book_id}/chunks/{seq}/signed-url")
async def generate_chunk_signed_url_alias(
    book_id: str,
    seq: int,
    expires_in: int = Query(3600, description="URL expiration time in seconds"),
    token: str = Depends(verify_authentication)
) -> Dict[str, Any]:
    """Alias for /api/v1/books/{book_id}/chunks/{seq}/signed-url - Generate signed URL for audio chunk."""
    try:
        # Verify book exists
        book = db_manager.get_book(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Generate signed URL
        signed_url = generate_signed_url(book_id, seq, token, expires_in)
        
        return {
            "signed_url": signed_url,
            "expires_in": expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate signed URL: {str(e)}"
        )


@app.get("/books/{book_id}/chunks/{seq}")
async def get_audio_chunk_alias(
    book_id: str, 
    seq: int,
    request: Request
):
    """Alias for /api/v1/books/{book_id}/chunks/{seq} - Stream audio chunk."""
    return await get_audio_chunk(book_id, seq, request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 