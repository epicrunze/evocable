#!/usr/bin/env python3

print("Starting auth test")

from fastapi import Query, Request, Depends, HTTPException, status
from typing import Optional

print("FastAPI imports successful")

from auth_models import session_manager

print("Session manager imported")

def test_auth_func(request: Request = Depends(), query_token: str = Query(None, alias="token")) -> str:
    """Test authentication function."""
    print("[AUTH DEBUG] ===== FUNCTION CALLED =====")
    print("[AUTH DEBUG] Incoming request headers:", dict(request.headers))
    print("[AUTH DEBUG] Query token:", query_token)
    return "test"

print("Auth function defined successfully")

print("Test completed") 