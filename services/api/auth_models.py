"""Authentication models for the Audiobook API service."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field
import uuid
import hashlib
import hmac
import os
from jose import JWTError, jwt


class LoginRequest(BaseModel):
    """Request model for user login."""
    apiKey: str = Field(
        ..., 
        description="API key for authentication",
        example="default-dev-key"
    )
    remember: Optional[bool] = Field(
        default=False, 
        description="Whether to remember the session (extends expiry to 30 days)",
        example=False
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "apiKey": "default-dev-key",
                    "remember": False
                },
                {
                    "apiKey": "prod-api-key-12345",
                    "remember": True
                }
            ]
        }
    }


class User(BaseModel):
    """User model for authentication responses."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")


class LoginResponse(BaseModel):
    """Response model for successful login."""
    sessionToken: str = Field(..., description="Session token for API authentication")
    expiresAt: str = Field(..., description="Token expiration time in ISO format")
    user: User = Field(..., description="User information")


class RefreshResponse(BaseModel):
    """Response model for token refresh."""
    sessionToken: str = Field(..., description="New session token")
    expiresAt: str = Field(..., description="New token expiration time in ISO format")
    user: User = Field(..., description="User information")


class LogoutResponse(BaseModel):
    """Response model for logout."""
    message: str = Field(..., description="Logout confirmation message")


class SessionManager:
    """Manages authentication sessions and tokens."""
    
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.default_expiry_hours = 24
        self.remember_expiry_hours = 24 * 30  # 30 days
        
    def create_session_token(self, user_id: str, remember: bool = False) -> tuple[str, datetime]:
        """Create a new session token."""
        expiry_hours = self.remember_expiry_hours if remember else self.default_expiry_hours
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        payload = {
            "sub": user_id,
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "jti": str(uuid.uuid4()),  # Unique token ID
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires_at
    
    def validate_session_token(self, token: str) -> Optional[dict]:
        """Validate a session token and return payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate the API key."""
        valid_api_key = os.getenv("API_KEY", "default-dev-key")
        return api_key == valid_api_key
    
    def get_user_info(self, user_id: str) -> User:
        """Get user information by ID."""
        # For now, return a simple admin user
        # In production, this would query a user database
        return User(
            id=user_id,
            username="admin"
        )
    
    def refresh_session_token(self, token: str) -> Optional[tuple[str, datetime, User]]:
        """Refresh a session token if valid."""
        payload = self.validate_session_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Create new token with same expiry duration as original
        new_token, expires_at = self.create_session_token(user_id, remember=True)
        user = self.get_user_info(user_id)
        
        return new_token, expires_at, user


# Global session manager instance
session_manager = SessionManager() 