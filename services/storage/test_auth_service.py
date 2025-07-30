"""Tests for user authentication service."""

import pytest
import asyncio
import uuid
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import ValidationError

# Add the storage service directory to Python path
storage_path = Path(__file__).parent
sys.path.insert(0, str(storage_path))

# Import our modules
from user_service import (
    UserService, UserCreateRequest, UserUpdateRequest, UserResponse
)
from main import User, Base

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


class TestUserService:
    """Test suite for UserService."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            test_db_path = tmp_db.name
        
        test_db_url = f"sqlite:///{test_db_path}"
        
        # Create engine and tables
        engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        yield session
        
        # Cleanup
        session.close()
        os.unlink(test_db_path)
    
    @pytest.fixture
    def user_service(self, db_session):
        """Create UserService instance."""
        return UserService(db_session)
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!"
        )
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, sample_user_data):
        """Test successful user creation."""
        user = await user_service.create_user(sample_user_data)
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert isinstance(user.id, str)
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, user_service, sample_user_data):
        """Test user creation with duplicate username."""
        # Create first user
        await user_service.create_user(sample_user_data)
        
        # Try to create second user with same username
        duplicate_data = UserCreateRequest(
            username="testuser",  # Same username
            email="different@example.com",
            password="TestPassword123!"
        )
        
        with pytest.raises(ValueError, match="Username already exists"):
            await user_service.create_user(duplicate_data)
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, sample_user_data):
        """Test user creation with duplicate email."""
        # Create first user
        await user_service.create_user(sample_user_data)
        
        # Try to create second user with same email
        duplicate_data = UserCreateRequest(
            username="differentuser",
            email="test@example.com",  # Same email
            password="TestPassword123!"
        )
        
        with pytest.raises(ValueError, match="Email already exists"):
            await user_service.create_user(duplicate_data)
    
    async def test_get_user_by_email(self, db_session):
        """Test getting user by email."""
        user_service = UserService(db_session)
        
        # Create a test user
        user_data = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        created_user = await user_service.create_user(user_data)
        
        # Test getting user by email
        retrieved_user = user_service.get_user_by_email("test@example.com")
        
        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"
        assert retrieved_user.email == "test@example.com"
    
    async def test_get_user_by_email_not_found(self, db_session):
        """Test getting user by email when user doesn't exist."""
        user_service = UserService(db_session)
        
        user = user_service.get_user_by_email("nonexistent@example.com")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, sample_user_data):
        """Test retrieving user by ID."""
        # Create user
        created_user = await user_service.create_user(sample_user_data)
        
        # Retrieve by ID
        retrieved_user = await user_service.get_user_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "testuser"
    
    async def test_authenticate_user_success(self, db_session):
        """Test successful user authentication."""
        user_service = UserService(db_session)
        
        # Create a test user
        user_data = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user_data)
        
        # Test authentication
        authenticated_user = user_service.authenticate_user(
            "test@example.com", "TestPass123!"
        )
        
        assert authenticated_user is not None
        assert authenticated_user.username == "testuser"
        assert authenticated_user.email == "test@example.com"
    
    async def test_authenticate_user_wrong_password(self, db_session):
        """Test authentication with wrong password."""
        user_service = UserService(db_session)
        
        # Create a test user
        user_data = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user_data)
        
        # Test authentication with wrong password
        authenticated_user = user_service.authenticate_user(
            "test@example.com", "WrongPassword123!"
        )
        
        assert authenticated_user is None
    
    async def test_authenticate_user_inactive(self, db_session):
        """Test authentication with inactive user."""
        user_service = UserService(db_session)
        
        # Create a test user
        user_data = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user_data)
        
        # Deactivate the user
        user = user_service.get_user_by_email("test@example.com")
        user.is_active = False
        db_session.commit()
        
        # Test authentication with inactive user
        authenticated_user = user_service.authenticate_user(
            "test@example.com", "TestPass123!"
        )
        
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_service, sample_user_data):
        """Test user update."""
        # Create user
        created_user = await user_service.create_user(sample_user_data)
        
        # Update user
        update_data = UserUpdateRequest(
            username="updateduser",
            is_verified=True
        )
        
        updated_user = await user_service.update_user(created_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.username == "updateduser"
        assert updated_user.is_verified is True
        assert updated_user.email == "test@example.com"  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, sample_user_data):
        """Test user deactivation."""
        # Create user
        created_user = await user_service.create_user(sample_user_data)
        
        # Deactivate user
        success = await user_service.deactivate_user(created_user.id)
        assert success is True
        
        # Verify user is deactivated
        user = await user_service.get_user_by_id(created_user.id)
        assert user.is_active is False
    
    @pytest.mark.asyncio
    async def test_activate_user(self, user_service, sample_user_data):
        """Test user activation."""
        # Create and deactivate user
        created_user = await user_service.create_user(sample_user_data)
        await user_service.deactivate_user(created_user.id)
        
        # Reactivate user
        success = await user_service.activate_user(created_user.id)
        assert success is True
        
        # Verify user is active
        user = await user_service.get_user_by_id(created_user.id)
        assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_verify_user_email(self, user_service, sample_user_data):
        """Test email verification."""
        # Create user
        created_user = await user_service.create_user(sample_user_data)
        
        # Verify email
        success = await user_service.verify_user_email(created_user.id)
        assert success is True
        
        # Check verification status
        user = await user_service.get_user_by_id(created_user.id)
        assert user.is_verified is True
    
    async def test_change_password(self, db_session):
        """Test changing user password."""
        user_service = UserService(db_session)
        
        # Create a test user
        user_data = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user_data)
        
        user = user_service.get_user_by_email("test@example.com")
        
        # Change password
        success = await user_service.change_password(
            user.id, "TestPass123!", "NewPass123!"
        )
        
        assert success is True
        
        # Verify old password doesn't work
        authenticated_user = user_service.authenticate_user(
            "test@example.com", "TestPass123!"
        )
        assert authenticated_user is None
        
        # Verify new password works
        authenticated_user = user_service.authenticate_user(
            "test@example.com", "NewPass123!"
        )
        assert authenticated_user is not None
    
    async def test_list_users(self, db_session):
        """Test listing users."""
        user_service = UserService(db_session)
        
        # Create test users
        user1_data = UserCreateRequest(
            username="user1",
            email="user1@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user1_data)
        
        user2_data = UserCreateRequest(
            username="user2",
            email="user2@example.com",
            password="TestPass123!"
        )
        await user_service.create_user(user2_data)
        
        # List all users
        users = await user_service.list_users()
        
        assert len(users) >= 2
        
        # List active users only
        active_users = await user_service.list_users(active_only=True)
        assert len(active_users) >= 2
    
    @pytest.mark.asyncio
    async def test_get_user_count(self, user_service):
        """Test user count."""
        # Initially should be 0
        count = await user_service.get_user_count()
        assert count == 0
        
        # Create users
        users_data = [
            UserCreateRequest(username="user1", email="user1@example.com", password="Pass123!"),
            UserCreateRequest(username="user2", email="user2@example.com", password="Pass123!")
        ]
        
        for user_data in users_data:
            await user_service.create_user(user_data)
        
        # Count should be 2
        count = await user_service.get_user_count()
        assert count == 2


class TestUserValidation:
    """Test user validation logic."""
    
    def test_valid_user_creation_request(self):
        """Test valid user creation request."""
        request = UserCreateRequest(
            username="validuser",
            email="valid@example.com",
            password="ValidPass123!"
        )
        
        assert request.username == "validuser"
        assert request.email == "valid@example.com"
        assert request.password == "ValidPass123!"
    
    def test_invalid_username_characters(self):
        """Test username with invalid characters."""
        with pytest.raises(ValueError, match="Username can only contain"):
            UserCreateRequest(
                username="invalid user!",  # Spaces and special chars not allowed
                email="test@example.com",
                password="ValidPass123!"
            )
    
    def test_weak_password(self):
        """Test weak password validation."""
        with pytest.raises(ValidationError, match="String should have at least 8 characters"):
            UserCreateRequest(
                username="testuser",
                email="test@example.com",
                password="weak"  # Too weak
            )
    
    def test_invalid_email(self):
        """Test invalid email format."""
        with pytest.raises(ValueError):
            UserCreateRequest(
                username="testuser",
                email="invalid-email",  # Invalid format
                password="ValidPass123!"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 