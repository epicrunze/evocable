#!/usr/bin/env python3

print("Starting test import")

# Import the same modules as main.py
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

print("Basic imports completed")

from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import httpx

print("FastAPI imports completed")

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

print("Models imported")

# Import authentication models
from auth_models import (
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    LogoutResponse,
    User,
    session_manager
)

print("Auth models imported")

# Import background task processing
from background_tasks import pipeline

print("Background tasks imported")

# Security
security = HTTPBearer()

print("Security setup completed")

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

print("verify_authentication function defined")

def get_optional_credentials(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Get optional Authorization header credentials."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return None

print("get_optional_credentials function defined")

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

print("verify_authentication_query function defined")

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

print("generate_signed_url function defined")

print("All functions defined successfully!") 