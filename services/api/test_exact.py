#!/usr/bin/env python3

print("Starting exact test")

from fastapi import Query, Request, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional
from auth_models import session_manager

print("Imports successful")

def get_optional_credentials(request: Request) -> Optional[HTTPAuthorizationCredentials]:
    """Get optional Authorization header credentials."""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return None

print("get_optional_credentials defined")

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

print("verify_authentication_query defined")

print("Test completed") 