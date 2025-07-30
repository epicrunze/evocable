"""Authentication models for the Audiobook API service."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
import uuid
import hashlib
import hmac
import os
import re
from jose import JWTError, jwt


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Username (3-50 characters, letters, numbers, underscore, hyphen only)",
        example="johndoe"
    )
    email: EmailStr = Field(
        ..., 
        description="Valid email address",
        example="john@example.com"
    )
    password: str = Field(
        ..., 
        min_length=8,
        max_length=128,
        description="Strong password (8+ chars, mixed case, numbers, special chars)",
        example="MySecurePass123!"
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation (must match password)",
        example="MySecurePass123!"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        errors = []
        
        if not re.search(r'[A-Z]', v):
            errors.append('at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            errors.append('at least one lowercase letter')
        if not re.search(r'\d', v):
            errors.append('at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append('at least one special character')
        
        if errors:
            raise ValueError(f'Password must contain {", ".join(errors)}')
        
        return v
    
    @model_validator(mode='after')
    def validate_password_match(self):
        """Ensure password and confirm_password match."""
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "johndoe",
                    "email": "john@example.com",
                    "password": "MySecurePass123!",
                    "confirm_password": "MySecurePass123!"
                }
            ]
        }
    }


class NewLoginRequest(BaseModel):
    """Request model for email/password login."""
    email: EmailStr = Field(
        ..., 
        description="Email address",
        example="john@example.com"
    )
    password: str = Field(
        ..., 
        description="User password",
        example="MySecurePass123!"
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
                    "email": "john@example.com",
                    "password": "MySecurePass123!",
                    "remember": False
                }
            ]
        }
    }


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


class UserProfile(BaseModel):
    """Comprehensive user profile model."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    is_active: bool = Field(..., description="Whether user account is active")
    is_verified: bool = Field(..., description="Whether user email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "johndoe",
                    "email": "john@example.com",
                    "is_active": True,
                    "is_verified": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
    }


class UserUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        description="New username (optional)"
    )
    email: Optional[EmailStr] = Field(
        None, 
        description="New email address (optional)"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format."""
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
            return v.lower()
        return v


class PasswordResetRequest(BaseModel):
    """Request model for password reset."""
    email: EmailStr = Field(
        ..., 
        description="Email address for password reset",
        example="john@example.com"
    )


class PasswordResetConfirm(BaseModel):
    """Request model for confirming password reset."""
    reset_token: str = Field(
        ..., 
        description="Password reset token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    new_password: str = Field(
        ..., 
        min_length=8,
        max_length=128,
        description="New password",
        example="NewSecurePass123!"
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation",
        example="NewSecurePass123!"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        errors = []
        
        if not re.search(r'[A-Z]', v):
            errors.append('at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            errors.append('at least one lowercase letter')
        if not re.search(r'\d', v):
            errors.append('at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append('at least one special character')
        
        if errors:
            raise ValueError(f'Password must contain {", ".join(errors)}')
        
        return v
    
    @model_validator(mode='after')
    def validate_password_match(self):
        """Ensure new_password and confirm_password match."""
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class ChangePasswordRequest(BaseModel):
    """Request model for changing password."""
    current_password: str = Field(
        ..., 
        description="Current password",
        example="CurrentPass123!"
    )
    new_password: str = Field(
        ..., 
        min_length=8,
        max_length=128,
        description="New password",
        example="NewSecurePass123!"
    )
    confirm_password: str = Field(
        ..., 
        description="Password confirmation",
        example="NewSecurePass123!"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        errors = []
        
        if not re.search(r'[A-Z]', v):
            errors.append('at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            errors.append('at least one lowercase letter')
        if not re.search(r'\d', v):
            errors.append('at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append('at least one special character')
        
        if errors:
            raise ValueError(f'Password must contain {", ".join(errors)}')
        
        return v
    
    @model_validator(mode='after')
    def validate_password_match(self):
        """Ensure new_password and confirm_password match."""
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


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
    """Enhanced session manager with user service integration."""
    
    def __init__(self, user_service=None):
        """Initialize session manager with optional user service."""
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.default_expiry_hours = 24
        self.remember_expiry_hours = 24 * 30  # 30 days
        self.password_reset_expiry_minutes = int(os.getenv("PASSWORD_RESET_EXPIRY", "15"))
        self.user_service = user_service
        
    def create_session_token(self, user_id: str, username: str = None, remember: bool = False) -> tuple[str, datetime]:
        """Create a new session token with user information."""
        expiry_hours = self.remember_expiry_hours if remember else self.default_expiry_hours
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        payload = {
            "sub": user_id,
            "username": username,
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "jti": str(uuid.uuid4()),  # Unique token ID
            "type": "session"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires_at
    
    def create_reset_token(self, user_id: str, email: str) -> tuple[str, datetime]:
        """Create a password reset token."""
        expires_at = datetime.utcnow() + timedelta(minutes=self.password_reset_expiry_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "jti": str(uuid.uuid4()),
            "type": "password_reset"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires_at
    
    def validate_session_token(self, token: str) -> Optional[dict]:
        """Validate a session token and return payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            # Ensure this is a session token
            if payload.get("type") != "session":
                return None
            return payload
        except JWTError:
            return None
    
    def validate_reset_token(self, token: str) -> Optional[dict]:
        """Validate a password reset token and return payload if valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            # Ensure this is a reset token
            if payload.get("type") != "password_reset":
                return None
            return payload
        except JWTError:
            return None
    

    
    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Authenticate user with email and password using user service."""
        if not self.user_service:
            return None
        
        try:
            user = await self.user_service.authenticate_user(email, password)
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified
                }
        except Exception:
            pass
        
        return None
    
    async def get_user_from_token(self, token: str) -> Optional[dict]:
        """Get user information from a valid token."""
        payload = self.validate_session_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # If we have a user service, get fresh user data
        if self.user_service:
            try:
                user_response = await self.user_service.get_user_by_id(user_id)
                if user_response:
                    return {
                        "id": user_response.id,
                        "username": user_response.username,
                        "email": user_response.email,
                        "is_active": user_response.is_active,
                        "is_verified": user_response.is_verified
                    }
            except Exception:
                pass
        
        # Fallback to token payload (for backwards compatibility)
        return {
            "id": user_id,
            "username": payload.get("username", "unknown"),
            "email": payload.get("email", ""),
            "is_active": True,
            "is_verified": True
        }
    
    def get_user_info(self, user_id: str) -> User:
        """Get basic user information by ID (legacy method)."""
        return User(
            id=user_id,
            username="admin" if user_id == "00000000-0000-0000-0000-000000000001" else "user"
        )
    
    def refresh_session_token(self, token: str) -> Optional[tuple[str, datetime, User]]:
        """Refresh a session token if valid."""
        payload = self.validate_session_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        username = payload.get("username")
        if not user_id:
            return None
        
        # Create new token with same expiry duration as original
        new_token, expires_at = self.create_session_token(user_id, username, remember=True)
        user = self.get_user_info(user_id)
        
        return new_token, expires_at, user


# Global session manager instance
session_manager = SessionManager() 