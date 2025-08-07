"""FastAPI application for Audiobook Server API Gateway."""

print("MAIN.PY TOP LEVEL EXECUTED - UNIQUE TEST PRINT")

import os
import sqlite3
import asyncio
from pathlib import Path as FilePath
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import hmac
import hashlib
import time
from urllib.parse import urlencode
from datetime import datetime

print("DEBUG: Basic imports completed")

# Validate critical environment variables early
try:
    from env_validation import validate_critical_env_vars
    validate_critical_env_vars()
    print("DEBUG: Environment validation passed")
except ImportError:
    print("WARNING: Environment validation module not available")
except RuntimeError as e:
    print(f"FATAL: Environment validation failed: {e}")
    raise

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile, BackgroundTasks, Query, Request, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded



# Import our data models
from models import (
    DatabaseManager, 
    BookSubmissionRequest, 
    BookResponse, 
    BookStatusResponse,
    ChunkListResponse,
    ChunkInfo,
    BatchSignedUrlRequest,
    BatchSignedUrlResponse,
    ErrorResponse,
    BookStatus,
    BookFormat
)

# Import authentication models
from auth_models import (
    RegisterRequest,
    NewLoginRequest,
    LoginResponse,
    RefreshResponse,
    LogoutResponse,
    User,
    UserProfile,
    UserUpdateRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    SessionManager
)

# Import background task processing
from background_tasks import pipeline

# Security
security = HTTPBearer(auto_error=False)  # Don't auto-raise 403, let us handle missing auth with 401

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
        }
    ],
    lifespan=lifespan
)
print("DEBUG: FastAPI app initialized successfully")

# CORS handled by FastAPI for service independence and multi-app nginx setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type", 
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Request-ID",
        "If-None-Match",
        "Range"
    ],
)

# Rate limiting setup
print("DEBUG: Setting up rate limiting")
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
print("DEBUG: Rate limiting configured")

# Security middleware for headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy (basic)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    
    return response

# Authentication event logging middleware
@app.middleware("http")
async def log_auth_events(request: Request, call_next):
    """Log authentication-related events."""
    import logging
    
    # Set up logging if not already configured
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("auth_events")
    
    # Log authentication requests
    if request.url.path.startswith("/auth/"):
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        logger.info(
            f"Auth request: {request.method} {request.url.path} "
            f"from {client_ip} UA: {user_agent[:100]}"
        )
    
    response = await call_next(request)
    
    # Log failed authentication attempts
    if request.url.path.startswith("/auth/") and response.status_code in [401, 403]:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning(
            f"Auth failure: {request.method} {request.url.path} "
            f"from {client_ip} status: {response.status_code}"
        )
    
    return response

print("DEBUG: Security middleware configured")



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

# User service integration for authentication
print("DEBUG: Setting up user service integration")

class StorageBookService:
    """Book service that communicates with storage service."""
    
    def __init__(self, storage_url: str):
        self.storage_url = storage_url.rstrip('/')
        self.http_client = httpx.AsyncClient()
    
    async def create_book(self, title: str, format: str, user_id: str):
        """Create book via storage service."""
        try:
            book_data = {
                "title": title,
                "format": format,
                "user_id": user_id
            }
            response = await self.http_client.post(
                f"{self.storage_url}/books",
                json=book_data
            )
            
            if response.status_code == 201:
                return response.json()
            else:
                print(f"DEBUG: Create book failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"DEBUG: Create book error: {e}")
            return None
    
    async def get_books(self, user_id: str = None, page: int = 1, per_page: int = 50):
        """Get books via storage service."""
        try:
            params = {"page": page, "per_page": per_page}
            if user_id:
                params["user_id"] = user_id
                
            response = await self.http_client.get(
                f"{self.storage_url}/books",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"DEBUG: Get books error: {e}")
            return None
    
    async def get_book_by_id(self, book_id: str, user_id: str = None):
        """Get book by ID via storage service."""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            url = f"{self.storage_url}/books/{book_id}"
            print(f"DEBUG SERVICE: GET {url} with params={params}")
            
            response = await self.http_client.get(url, params=params)
            
            print(f"DEBUG SERVICE: Response status={response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"DEBUG SERVICE: Response data={result}")
                return result
            else:
                print(f"DEBUG SERVICE: Response text={response.text}")
            return None
        except Exception as e:
            print(f"DEBUG: Get book by ID error: {e}")
            return None
    
    async def update_book_status(self, book_id: str, status: str, user_id: str = None):
        """Update book status via storage service."""
        try:
            params = {"status": status}
            if user_id:
                params["user_id"] = user_id
                
            response = await self.http_client.put(
                f"{self.storage_url}/books/{book_id}/status",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"DEBUG: Update book status error: {e}")
            return None
    
    async def delete_book(self, book_id: str, user_id: str = None):
        """Delete book via storage service."""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
                
            response = await self.http_client.delete(
                f"{self.storage_url}/books/{book_id}",
                params=params
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"DEBUG: Delete book error: {e}")
            return None


# Legacy HTTP-based user service code removed - now using Redis queues
# Simple user classes moved to redis_user_service.py

# Create user service instance - now using Redis queues
from redis_user_service import RedisUserService
user_service = RedisUserService()

# Create book service instance
book_service = StorageBookService(os.getenv("STORAGE_URL", "http://storage:8001"))

# Create session manager with user service
session_manager = SessionManager(user_service=user_service)
print("DEBUG: User service, book service, and session manager created successfully")


async def _signal_file_cleanup(book_id: str, user_id: str):
    """Signal other services to clean up their files for a deleted book."""
    try:
        import redis
        import json
        from datetime import datetime
        
        # Connect to Redis
        redis_client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        
        # Create cleanup message
        cleanup_message = {
            "book_id": book_id,
            "user_id": user_id,
            "action": "cleanup_files",
            "timestamp": datetime.utcnow().isoformat(),
            "requested_by": "api_service"
        }
        
        # Send to cleanup queue for all services to process
        redis_client.lpush("cleanup_queue", json.dumps(cleanup_message))
        print(f"DEBUG: Sent cleanup signal for book {book_id} to cleanup_queue")
        
    except Exception as e:
        print(f"Warning: Failed to signal file cleanup: {e}")
        # Don't fail the delete operation if cleanup signaling fails


def verify_authentication(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Verify authentication from Authorization header (API key or session token)."""
    # Check if credentials are missing (no Authorization header)
    if not credentials:
        print("[AUTH DEBUG] No Authorization header provided, raising 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    token = credentials.credentials
    print(f"[AUTH DEBUG] Verifying token: {token[:10]}...")
    
    # First, try to validate as session token
    payload = session_manager.validate_session_token(token)
    print(f"[AUTH DEBUG] Token validation result: {payload}")
    
    if payload:
        print(f"[AUTH DEBUG] Token is valid, returning token")
        return token
    
    # If session token validation fails, raise authentication error
    print(f"[AUTH DEBUG] Token validation failed, raising 401")
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

        except Exception as e:
            print("[AUTH DEBUG] Exception during query token validation:", e)
    else:
        print("[AUTH DEBUG] No query token present")
    print("[AUTH DEBUG] Authentication failed - no valid credentials provided")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials"
    )

print("DEBUG: verify_authentication_query function defined")


# User context dependency
async def get_current_user(token: str = Depends(verify_authentication)) -> dict:
    """Get current user context from authentication token."""
    try:
        # Get user information from token
        user_info = await session_manager.get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = user_info.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing user ID"
            )
        
        # For API key users (admin), return the token info directly
        if user_id == "00000000-0000-0000-0000-000000000001":
            return {
                "id": user_id,
                "username": user_info.get("username", "admin"),
                "email": "admin@evocable.local",
                "is_active": True,
                "is_verified": True,
                "is_admin": True
            }
        
        # For regular users, get fresh data from storage service
        user_profile = await user_service.get_user_by_id(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user_profile.id,
            "username": user_profile.username,
            "email": user_profile.email,
            "is_active": user_profile.is_active,
            "is_verified": user_profile.is_verified,
            "is_admin": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current user: {str(e)}"
        )

print("DEBUG: get_current_user dependency function defined")

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





# New user authentication endpoints
@app.post(
    "/auth/register", 
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register new user account",
    description="""
    Register a new user account with email and password.
    
    ## Features
    
    - **Email validation**: Ensures valid email format
    - **Password strength**: Enforces strong password requirements
    - **Username validation**: Alphanumeric characters, underscores, and hyphens only
    - **Duplicate prevention**: Checks for existing usernames and emails
    
    ## Password Requirements
    
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one number
    - At least one special character
    - Password and confirmation must match
    """,
    responses={
        201: {"description": "User successfully created"},
        400: {"description": "Username or email already exists"},
        422: {"description": "Validation error (weak password, invalid format, etc.)"}
    }
)
# @limiter.limit("100/minute" if os.getenv("DEBUG", "false").lower() == "true" else "3/hour")
async def register_user(request: Request, request_data: RegisterRequest) -> UserProfile:
    """Register a new user account."""
    import logging
    logger = logging.getLogger("registration")
    logger.error("DEBUG: ======== INSIDE REGISTER_USER FUNCTION ========")
    try:
        # Prepare user data for storage service
        user_data = {
            "username": request_data.username,
            "email": request_data.email,
            "password": request_data.password
        }
        
        logger.error(f"DEBUG: Registration - user_data: {user_data}")
        logger.error("DEBUG: About to call user_service.create_user")
        
        # Create user via storage service
        result = await user_service.create_user(user_data)
        
        logger.error("DEBUG: user_service.create_user completed")
        
        logger.error(f"DEBUG: Registration - result from storage service: {result}")
        
        if "error" in result and result["error"] is not None:
            # Handle errors from storage service
            error_msg = result["error"]
            if "already exists" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
        
        # Convert storage service response to UserProfile
        user_data = result["user"]
        created_at = None
        updated_at = None
        
        if user_data.get("created_at"):
            created_at = datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00"))
        if user_data.get("updated_at"):
            updated_at = datetime.fromisoformat(user_data["updated_at"].replace("Z", "+00:00"))
        
        return UserProfile(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            is_active=user_data["is_active"],
            is_verified=user_data["is_verified"],
            created_at=created_at,
            updated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger("registration")
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Registration traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post(
    "/auth/login/email",
    response_model=LoginResponse,
    tags=["Authentication"], 
    summary="Login with email and password",
    description="""
    Authenticate with email and password to receive a session token.
    
    ## Features
    
    - **Email/password authentication**: Secure login using user credentials
    - **Remember me**: Optional extended session duration (30 days vs 24 hours)
    - **JWT tokens**: Secure session tokens with user information
    - **Account validation**: Checks for active account status
    
    ## Usage
    
    Use this endpoint for user authentication instead of API keys.
    The returned session token can be used for all authenticated requests.
    """,
    responses={
        200: {"description": "Authentication successful"},
        401: {"description": "Invalid email or password"},
        422: {"description": "Invalid request format"}
    }
)
@limiter.limit("100/minute" if os.getenv("DEBUG", "false").lower() == "true" else "5/minute")
async def login_with_email(request: Request, request_data: NewLoginRequest) -> LoginResponse:
    """Authenticate user with email and password."""
    try:
        # Authenticate user via storage service
        authenticated_user = await session_manager.authenticate_user(request_data.email, request_data.password)
        
        if not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user account is active
        if not authenticated_user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Create session token
        user_id = authenticated_user["id"]
        username = authenticated_user["username"]
        session_token, expires_at = session_manager.create_session_token(
            user_id,
            username=username,
            remember=request_data.remember or False
        )
        
        # Create user object for response
        user = User(
            id=user_id,
            username=username
        )
        
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


@app.get(
    "/auth/profile",
    response_model=UserProfile,
    tags=["Authentication"],
    summary="Get user profile",
    description="""
    Get the current user's profile information.
    
    ## Returns
    
    - **User details**: ID, username, email, account status
    - **Account info**: Creation date, verification status, active status
    - **No sensitive data**: Password and other sensitive information excluded
    """,
    responses={
        200: {"description": "Profile retrieved successfully"},
        401: {"description": "Invalid or expired token"}
    }
)
async def get_user_profile(token: str = Depends(verify_authentication)) -> UserProfile:
    """Get current user profile."""
    try:
        # Get user information from token
        user_info = await session_manager.get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = user_info.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get fresh user data from storage service
        user_profile_response = await user_service.get_user_by_id(user_id)
        
        if not user_profile_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Convert to UserProfile response
        created_at = datetime.utcnow()  # Default fallback
        updated_at = datetime.utcnow()  # Default fallback
        
        if user_profile_response.created_at:
            try:
                created_at = datetime.fromisoformat(user_profile_response.created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass  # Use default fallback
        
        if user_profile_response.updated_at:
            try:
                updated_at = datetime.fromisoformat(user_profile_response.updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass  # Use default fallback
        
        return UserProfile(
            id=user_profile_response.id,
            username=user_profile_response.username,
            email=user_profile_response.email,
            is_active=user_profile_response.is_active,
            is_verified=user_profile_response.is_verified,
            created_at=created_at,
            updated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile retrieval failed: {str(e)}"
        )


@app.put(
    "/auth/profile",
    response_model=UserProfile,
    tags=["Authentication"],
    summary="Update user profile",
    description="""
    Update the current user's profile information.
    
    ## Updateable Fields
    
    - **Username**: Must be unique and follow validation rules
    - **Email**: Must be valid email format and unique
    
    ## Validation
    
    - Username: 3-50 characters, alphanumeric, underscores, hyphens only
    - Email: Valid email format, uniqueness checked
    """,
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"description": "Username or email already exists"},
        401: {"description": "Invalid or expired token"},
        422: {"description": "Validation error"}
    }
)
@limiter.limit("100/minute" if os.getenv("DEBUG", "false").lower() == "true" else "10/minute")
async def update_user_profile(
    request: Request,
    request_data: UserUpdateRequest,
    token: str = Depends(verify_authentication)
) -> UserProfile:
    """Update current user profile."""
    try:
        # Get user information from token
        user_info = await session_manager.get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = user_info.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        if request_data.username is not None:
            update_data["username"] = request_data.username
        if request_data.email is not None:
            update_data["email"] = request_data.email
        
        # Don't update if no data provided
        if not update_data:
            # Just return current profile
            user_profile_response = await user_service.get_user_by_id(user_id)
            if not user_profile_response:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Parse timestamps
            created_at = datetime.utcnow()  # Default fallback
            updated_at = datetime.utcnow()  # Default fallback
            
            if user_profile_response.created_at:
                try:
                    created_at = datetime.fromisoformat(user_profile_response.created_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass  # Use default fallback
            
            if user_profile_response.updated_at:
                try:
                    updated_at = datetime.fromisoformat(user_profile_response.updated_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass  # Use default fallback
            
            return UserProfile(
                id=user_profile_response.id,
                username=user_profile_response.username,
                email=user_profile_response.email,
                is_active=user_profile_response.is_active,
                is_verified=user_profile_response.is_verified,
                created_at=created_at,
                updated_at=updated_at
            )
        
        # Update user via storage service
        result = await user_service.update_user(user_id, update_data)
        
        if "error" in result and result["error"] is not None:
            # Handle errors from storage service
            error_msg = result["error"]
            if "already exists" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            elif "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
        
        # Convert storage service response to UserProfile
        user_data = result["user"]
        created_at = None
        updated_at = None
        
        if user_data.get("created_at"):
            created_at = datetime.fromisoformat(user_data["created_at"].replace("Z", "+00:00"))
        if user_data.get("updated_at"):
            updated_at = datetime.fromisoformat(user_data["updated_at"].replace("Z", "+00:00"))
        
        return UserProfile(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            is_active=user_data["is_active"],
            is_verified=user_data["is_verified"],
            created_at=created_at,
            updated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@app.post(
    "/auth/change-password",
    tags=["Authentication"],
    summary="Change user password", 
    description="""
    Change the current user's password.
    
    ## Requirements
    
    - **Current password**: Must provide current password for verification
    - **New password**: Must meet strength requirements
    - **Confirmation**: New password must be confirmed
    
    ## Security
    
    - Validates current password before allowing change
    - Enforces strong password requirements
    - Passwords are securely hashed before storage
    """,
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Current password incorrect"},
        401: {"description": "Invalid or expired token"},
        422: {"description": "Password validation failed"}
    }
)
@limiter.limit("50/minute" if os.getenv("DEBUG", "false").lower() == "true" else "5/hour")
async def change_password(
    request: Request,
    request_data: ChangePasswordRequest,
    token: str = Depends(verify_authentication)
):
    """Change user password."""
    try:
        # Get user information from token
        user_info = await session_manager.get_user_from_token(token)
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_id = user_info.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Change password via storage service
        success = await user_service.change_password(
            user_id,
            request_data.current_password,
            request_data.new_password
        )
        
        if success:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password change failed: {str(e)}"
        )


@app.post(
    "/auth/forgot-password",
    tags=["Authentication"],
    summary="Request password reset",
    description="""
    Request a password reset token for the given email address.
    
    ## Process
    
    1. **Email verification**: Checks if email exists in system
    2. **Token generation**: Creates secure reset token with expiration
    3. **Email notification**: Sends reset instructions (placeholder for now)
    
    ## Security
    
    - Reset tokens expire after 15 minutes
    - Tokens are single-use and securely signed
    - No user information exposed for non-existent emails
    """,
    responses={
        200: {"description": "Reset email sent (if email exists)"},
        422: {"description": "Invalid email format"}
    }
)
@limiter.limit("50/minute" if os.getenv("DEBUG", "false").lower() == "true" else "3/hour")
async def forgot_password(request: Request, request_data: PasswordResetRequest):
    """Request password reset."""
    try:
        # Check if user exists (but don't reveal this information)
        user = await user_service.get_user_by_email(request_data.email)
        
        if user:
            # Generate reset token
            reset_token, expires_at = session_manager.create_reset_token(
                user_id=user.id,
                email=user.email
            )
            
            # TODO: In a real implementation, send email with reset link
            # For now, we'll log the token (NEVER do this in production!)
            print(f"Password reset token for {user.email}: {reset_token}")
            print(f"Token expires at: {expires_at}")
        
        # Always return the same message for security (don't reveal if email exists)
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )


@app.post(
    "/auth/reset-password",
    tags=["Authentication"],
    summary="Reset password with token",
    description="""
    Reset password using a valid reset token.
    
    ## Process
    
    1. **Token validation**: Verifies reset token is valid and not expired
    2. **Password validation**: Ensures new password meets requirements
    3. **Password update**: Securely hashes and stores new password
    4. **Token invalidation**: Prevents token reuse
    """,
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired reset token"},
        422: {"description": "Password validation failed"}
    }
)
@limiter.limit("50/minute" if os.getenv("DEBUG", "false").lower() == "true" else "5/hour")
async def reset_password(request: Request, request_data: PasswordResetConfirm):
    """Reset password with token."""
    try:
        # Validate the reset token
        payload = session_manager.validate_reset_token(request_data.token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Extract user info from token
        user_email = payload.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload"
            )
        
        # Reset the password via storage service
        success = await user_service.reset_password_by_email(
            email=user_email,
            new_password=request_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reset password"
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
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
async def list_books(current_user: dict = Depends(get_current_user)):
    """List books owned by the current user."""
    try:
        # Get books from storage service filtered by user
        books_response = await book_service.get_books(
            user_id=current_user["id"],
            page=1,
            per_page=100  # Large limit for now
        )
        
        if not books_response:
            return {"books": []}
        
        return books_response
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
    current_user: dict = Depends(get_current_user)
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
        
        file_extension = FilePath(file.filename).suffix.lower()
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
        
        # Create book record via storage service
        book_response = await book_service.create_book(
            title=title,
            format=book_format.value,
            user_id=current_user["id"]
        )
        
        if not book_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create book record in storage service"
            )
        
        book_id = book_response["id"]
        
        # Save file to storage (using same pattern as storage service)
        text_data_path = os.getenv("TEXT_DATA_PATH", "/tmp/data/text")
        book_dir = FilePath(f"{text_data_path}/uploads/{book_id}")
        book_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = book_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Update book status via storage service
        status_response = await book_service.update_book_status(
            book_id=book_id,
            status=BookStatus.PENDING.value,
            user_id=current_user["id"]
        )
        
        if not status_response:
            print(f"WARNING: Failed to update book status for {book_id}")
        
        # TODO: Store file path in storage service (for now, file is stored locally)
        
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
    current_user: dict = Depends(get_current_user)
):
    """Get book processing status."""
    try:
        # Get book from storage service with user ownership check
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        
        if not book_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found or access denied"
            )
        
        book = book_response  # Storage service returns the book data directly
        
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
            percent_complete=0.0,  # Storage service doesn't track progress yet
            error_message=None,    # Storage service doesn't track errors yet
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
    current_user: dict = Depends(get_current_user)
):
    """List available audio chunks for a book."""
    try:
        # Check if book exists and user has access
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        if not book_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found or access denied"
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
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate a signed URL for accessing an audio chunk."""
    print(f"DEBUG: Signed URL endpoint called with book_id={book_id}, seq={seq}, expires_in={expires_in}")
    try:
        # Verify book exists and user has access
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        if not book_response:
            print(f"DEBUG: Book {book_id} not found or access denied for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found or access denied"
            )
        
        print(f"DEBUG: Book {book_id} found, generating signed URL")
        # Create a session token for the current user (needed for signed URL)
        user_token, _ = session_manager.create_session_token(
            user_id=current_user["id"],
            username=current_user["username"]
        )
        # Generate signed URL
        signed_url = generate_signed_url(book_id, seq, user_token, expires_in)
        
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


@app.post(
    "/api/v1/books/{book_id}/chunks/batch-signed-urls", 
    response_model=BatchSignedUrlResponse,
    tags=["Audio"],
    summary="Generate batch signed URLs",
    description="""
    Generate signed URLs for multiple audio chunks in a single request to optimize streaming performance.
    
    ## Performance Benefits
    
    - **Reduced Network Overhead**: Get multiple URLs in one request instead of individual requests
    - **Parallel Loading**: Enable concurrent chunk prefetching
    - **Lower Latency**: Minimize round trips for smooth streaming
    
    ## Usage Strategy
    
    1. **Initial Load**: Request URLs for first 5-10 chunks
    2. **Progressive Loading**: As playback progresses, request next batch
    3. **Prefetching**: Always stay 3-5 chunks ahead of current playback
    
    ## Batch Limits
    
    - **Maximum**: 20 chunks per request to prevent abuse
    - **Minimum**: 1 chunk required
    - **Validation**: All chunk sequences must be non-negative integers
    
    ## Security
    
    - Same security as individual signed URLs
    - URLs expire based on `expires_in` parameter (default 1 hour)
    - Signed with HMAC to prevent tampering
    """,
    responses={
        200: {
            "description": "Batch signed URLs generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "book_id": "550e8400-e29b-41d4-a716-446655440000",
                        "signed_urls": {
                            "0": "https://server.epicrunze.com/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/0?expires=1640995200&signature=abc123&token=def456",
                            "1": "https://server.epicrunze.com/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/1?expires=1640995200&signature=ghi789&token=def456",
                            "2": "https://server.epicrunze.com/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/2?expires=1640995200&signature=jkl012&token=def456"
                        },
                        "expires_in": 3600,
                        "total_chunks": 3
                    }
                }
            }
        },
        400: {
            "description": "Invalid request - chunk validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_chunks": {
                            "summary": "Invalid chunk sequences",
                            "value": {
                                "detail": "Chunk sequence must be non-negative, got -1"
                            }
                        },
                        "too_many_chunks": {
                            "summary": "Batch size exceeded",
                            "value": {
                                "detail": "Maximum 20 chunks per batch request"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Book not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Book with ID 550e8400-e29b-41d4-a716-446655440000 not found"
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
        }
    }
)
async def generate_batch_signed_urls(
    book_id: str,
    request: BatchSignedUrlRequest,
    expires_in: int = Query(3600, description="URL expiration time in seconds"),
    current_user: dict = Depends(get_current_user)
) -> BatchSignedUrlResponse:
    """Generate signed URLs for multiple audio chunks at once."""
    print(f"DEBUG: Batch signed URL endpoint called with book_id={book_id}, user_id={current_user['id']}")
    try:
        # Verify book exists and user has access
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        print(f"DEBUG: Book response: {book_response}")
        if not book_response:
            print(f"DEBUG: Book {book_id} not found or access denied for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found or access denied"
            )
        
        # Get chunk sequences from request (already validated by Pydantic)
        chunk_sequences = request.chunks
        
        # Validate that chunks exist for this book (optional enhancement)
        # This could check against storage service to ensure chunks actually exist
        # For now, we'll generate URLs for all requested chunks
        
        # Create a session token for the current user (needed for signed URL)
        user_token, _ = session_manager.create_session_token(
            user_id=current_user["id"],
            username=current_user["username"]
        )
        
        # Generate signed URLs for all requested chunks
        signed_urls = {}
        failed_chunks = []
        
        for seq in chunk_sequences:
            try:
                signed_url = generate_signed_url(book_id, seq, user_token, expires_in)
                signed_urls[str(seq)] = signed_url
            except Exception as e:
                print(f"DEBUG: Failed to generate signed URL for chunk {seq}: {e}")
                failed_chunks.append(seq)
        
        # If any chunks failed, log warning but continue with successful ones
        if failed_chunks:
            print(f"WARNING: Failed to generate signed URLs for chunks: {failed_chunks}")
        
        # Return error if no URLs were generated successfully
        if not signed_urls:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate any signed URLs"
            )
        
        return BatchSignedUrlResponse(
            book_id=book_id,
            signed_urls=signed_urls,
            expires_in=expires_in,
            total_chunks=len(signed_urls)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch signed URLs: {str(e)}"
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
    request: Request,
    book_id: str, 
    seq: int
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
            audio_file_path = FilePath(chunk["file_path"])
            if not audio_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audio file not found: {chunk['file_path']}"
                )
            
            # Return file response with caching headers
            from fastapi.responses import FileResponse
            import hashlib
            
            # Generate ETag based on file path and modification time
            file_stat = audio_file_path.stat()
            etag_data = f"{audio_file_path}:{file_stat.st_mtime}:{file_stat.st_size}"
            etag = hashlib.md5(etag_data.encode()).hexdigest()
            
            response = FileResponse(
                path=str(audio_file_path),
                media_type="audio/ogg",
                filename=f"chunk_{seq:06d}.ogg"
            )
            
            # Add caching headers
            response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour cache
            response.headers["ETag"] = f'"{etag}"'
            
            # Check if client has cached version
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match and if_none_match.strip('"') == etag:
                from fastapi.responses import Response
                return Response(status_code=304)  # Not Modified
            
            return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream audio chunk: {str(e)}"
        )


@app.get("/debug/books/{book_id}/chunks")
async def debug_book_chunks(book_id: str, current_user: dict = Depends(get_current_user)):
    """Debug endpoint to see what's happening with chunks."""
    try:
        print(f"DEBUG: Getting chunks for book {book_id}")
        
        # Check if book exists and user has access
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        print(f"DEBUG: Book found: {book_response is not None}")
        if not book_response:
            return {"error": "Book not found or access denied"}
        
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
    current_user: dict = Depends(get_current_user)
):
    """Delete a book and all its associated data."""
    try:
        # Check if book exists and user has access
        print(f"DEBUG DELETE: user_id={current_user['id']}, book_id={book_id}")
        book_response = await book_service.get_book_by_id(book_id, user_id=current_user["id"])
        print(f"DEBUG DELETE: book_response={book_response}")
        if not book_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found or access denied"
            )
        
        # Delete from storage service
        delete_response = await book_service.delete_book(book_id, user_id=current_user["id"])
        if not delete_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete book from storage service"
            )
        
        # Clean up storage service chunks
        storage_url = os.getenv("STORAGE_URL", "http://storage:8001")
        try:
            async with httpx.AsyncClient() as client:
                # Delete chunks from storage database
                await client.delete(f"{storage_url}/books/{book_id}/audio-chunks")
        except Exception as e:
            print(f"Warning: Failed to delete chunks from storage service: {e}")
        
        # Signal other services to clean up their files
        await _signal_file_cleanup(book_id, current_user["id"])
        
        # Clean up files
        import shutil
        file_paths_to_remove = [
            f"/data/text/{book_id}",
            f"/data/wav/{book_id}"
            # Note: /data/ogg cleanup handled by transcoder service (API has read-only access)
        ]
        
        for path in file_paths_to_remove:
            try:
                if FilePath(path).exists():
                    shutil.rmtree(path)
                    print(f"Deleted directory: {path}")
            except Exception as e:
                print(f"Warning: Failed to delete {path}: {e}")
        
        return {"message": f"Successfully deleted book '{book_response['title']}' and all associated data"}
        
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

# REMOVED: Legacy endpoints have been deprecated and removed
# Frontend should now use the modern /api/v1/books/* endpoints instead
# 
# Legacy -> Modern endpoint mappings:
# GET /books -> GET /api/v1/books
# POST /books/upload -> POST /api/v1/books  
# GET /books/{book_id} -> GET /api/v1/books/{book_id}/status
# DELETE /books/{book_id} -> DELETE /api/v1/books/{book_id}
# GET /books/{book_id}/chunks -> GET /api/v1/books/{book_id}/chunks
# GET /books/{book_id}/chunks/{seq} -> GET /api/v1/books/{book_id}/chunks/{seq}
# POST /books/{book_id}/chunks/{seq}/signed-url -> POST /api/v1/books/{book_id}/chunks/{seq}/signed-url


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 