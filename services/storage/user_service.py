"""User service layer for authentication and user management."""

import uuid
import re
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field, field_validator
from passlib.context import CryptContext

# Import the User model - we'll need to update the import path
try:
    from main import User
except ImportError:
    # For testing purposes, we'll define a minimal User class
    from sqlalchemy import Column, String, Boolean, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
    
    class User(Base):
        __tablename__ = "users"
        id = Column(String, primary_key=True)
        username = Column(String, unique=True)
        email = Column(String, unique=True)
        password_hash = Column(String)
        is_active = Column(Boolean, default=True)
        is_verified = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=8)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdateRequest(BaseModel):
    """Request model for updating user information."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower() if v else v


class UserResponse(BaseModel):
    """Response model for user data (excludes sensitive information)."""
    id: str
    username: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True
    }


class UserService:
    """Service class for user management operations."""
    
    def __init__(self, db_session: Session):
        """Initialize the user service with a database session."""
        self.db = db_session
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        """Create a new user with validation."""
        try:
            # Check if username already exists
            existing_user = self.db.query(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email.lower())
            ).first()
            
            if existing_user:
                if existing_user.username == user_data.username:
                    raise ValueError("Username already exists")
                if existing_user.email == user_data.email.lower():
                    raise ValueError("Email already exists")
            
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                username=user_data.username,
                email=user_data.email.lower(),
                password_hash=self._hash_password(user_data.password),
                is_active=True,
                is_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            return UserResponse.model_validate(user)
            
        except IntegrityError as e:
            self.db.rollback()
            if "username" in str(e):
                raise ValueError("Username already exists")
            elif "email" in str(e):
                raise ValueError("Email already exists")
            else:
                raise ValueError("User creation failed")
        except Exception as e:
            self.db.rollback()
            raise e
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        return UserResponse.model_validate(user) if user else None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (returns full User object for authentication)."""
        return self.db.query(User).filter(User.email == email.lower()).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username (returns full User object for authentication)."""
        return self.db.query(User).filter(User.username == username.lower()).first()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(email)
        if not user or not user.is_active:
            return None
        
        if self._verify_password(password, user.password_hash):
            return user
        
        return None
    
    async def update_user(self, user_id: str, update_data: UserUpdateRequest) -> Optional[UserResponse]:
        """Update user information."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Check for username/email conflicts
            if update_data.username and update_data.username != user.username:
                existing = self.db.query(User).filter(
                    User.username == update_data.username,
                    User.id != user_id
                ).first()
                if existing:
                    raise ValueError("Username already exists")
            
            if update_data.email and update_data.email.lower() != user.email:
                existing = self.db.query(User).filter(
                    User.email == update_data.email.lower(),
                    User.id != user_id
                ).first()
                if existing:
                    raise ValueError("Email already exists")
            
            # Apply updates
            update_dict = update_data.model_dump(exclude_unset=True)
            if 'email' in update_dict:
                update_dict['email'] = update_dict['email'].lower()
            
            for field, value in update_dict.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(user)
            
            return UserResponse.model_validate(user)
            
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Update failed due to constraint violation")
        except Exception as e:
            self.db.rollback()
            raise e
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    async def activate_user(self, user_id: str) -> bool:
        """Activate a user account."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.is_active = True
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    async def verify_user_email(self, user_id: str) -> bool:
        """Mark user email as verified."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.is_verified = True
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password with current password verification."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Verify current password
            if not self._verify_password(current_password, user.password_hash):
                return False
            
            # Validate new password
            try:
                UserCreateRequest(
                    username="temp",
                    email="temp@example.com",
                    password=new_password
                )
            except ValueError:
                # Password doesn't meet requirements
                return False
            
            # Update password
            user.password_hash = self._hash_password(new_password)
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception:
            self.db.rollback()
            return False
    
    async def list_users(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[UserResponse]:
        """List users with pagination."""
        query = self.db.query(User)
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        users = query.offset(skip).limit(limit).all()
        return [UserResponse.model_validate(user) for user in users]
    
    async def get_user_count(self, active_only: bool = True) -> int:
        """Get total user count."""
        query = self.db.query(User)
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        return query.count()
    
    async def reset_password_by_email(self, email: str, new_password: str) -> bool:
        """Reset password for user with given email."""
        try:
            # Find user by email
            user = self.db.query(User).filter(User.email == email.lower()).first()
            if not user:
                return False
            
            # Hash the new password
            hashed_password = pwd_context.hash(new_password)
            
            # Update password
            user.password_hash = hashed_password
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Password reset error: {e}")
            return False