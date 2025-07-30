"""Tests for authentication models (Phase 2)."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from auth_models import (
    RegisterRequest,
    NewLoginRequest,
    UserProfile,
    UserUpdateRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    SessionManager
)


class TestRegisterRequest:
    """Test suite for RegisterRequest model."""
    
    def test_valid_registration(self):
        """Test valid registration request."""
        request = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="ValidPass123!",
            confirm_password="ValidPass123!"
        )
        
        assert request.username == "testuser"
        assert request.email == "test@example.com"
        assert request.password == "ValidPass123!"
        assert request.confirm_password == "ValidPass123!"
    
    def test_username_lowercase_conversion(self):
        """Test username is converted to lowercase."""
        request = RegisterRequest(
            username="TestUser",
            email="test@example.com",
            password="ValidPass123!",
            confirm_password="ValidPass123!"
        )
        
        assert request.username == "testuser"
    
    def test_invalid_username_characters(self):
        """Test username with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="test user!",  # Space and special character
                email="test@example.com",
                password="ValidPass123!",
                confirm_password="ValidPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "Username can only contain" in str(error["msg"])
    
    def test_username_too_short(self):
        """Test username too short."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="ab",  # Only 2 characters
                email="test@example.com",
                password="ValidPass123!",
                confirm_password="ValidPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "at least 3 characters" in str(error["msg"])
    
    def test_username_too_long(self):
        """Test username too long."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="a" * 51,  # 51 characters
                email="test@example.com",
                password="ValidPass123!",
                confirm_password="ValidPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "at most 50 characters" in str(error["msg"])
    
    def test_invalid_email(self):
        """Test invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="invalid-email",
                password="ValidPass123!",
                confirm_password="ValidPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "value_error"
    
    def test_password_too_short(self):
        """Test password too short."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="Short1!",  # Only 7 characters
                confirm_password="Short1!"
            )
        
        error = exc_info.value.errors()[0]
        assert "at least 8 characters" in str(error["msg"])
    
    def test_password_too_long(self):
        """Test password too long."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="a" * 129,  # 129 characters
                confirm_password="a" * 129
            )
        
        error = exc_info.value.errors()[0]
        assert "at most 128 characters" in str(error["msg"])
    
    def test_password_missing_uppercase(self):
        """Test password without uppercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="lowercase123!",
                confirm_password="lowercase123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "uppercase letter" in str(error["msg"])
    
    def test_password_missing_lowercase(self):
        """Test password without lowercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="UPPERCASE123!",
                confirm_password="UPPERCASE123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "lowercase letter" in str(error["msg"])
    
    def test_password_missing_number(self):
        """Test password without number."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="NoNumbersHere!",
                confirm_password="NoNumbersHere!"
            )
        
        error = exc_info.value.errors()[0]
        assert "one number" in str(error["msg"])
    
    def test_password_missing_special_char(self):
        """Test password without special character."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="NoSpecialChar123",
                confirm_password="NoSpecialChar123"
            )
        
        error = exc_info.value.errors()[0]
        assert "special character" in str(error["msg"])
    
    def test_password_mismatch(self):
        """Test password and confirm_password mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password="ValidPass123!",
                confirm_password="DifferentPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "do not match" in str(error["msg"])


class TestNewLoginRequest:
    """Test suite for NewLoginRequest model."""
    
    def test_valid_login_request(self):
        """Test valid login request."""
        request = NewLoginRequest(
            email="test@example.com",
            password="TestPassword123!",
            remember=True
        )
        
        assert request.email == "test@example.com"
        assert request.password == "TestPassword123!"
        assert request.remember is True
    
    def test_default_remember_false(self):
        """Test remember defaults to False."""
        request = NewLoginRequest(
            email="test@example.com",
            password="TestPassword123!"
        )
        
        assert request.remember is False
    
    def test_invalid_email(self):
        """Test invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            NewLoginRequest(
                email="invalid-email",
                password="TestPassword123!"
            )
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "value_error"


class TestUserProfile:
    """Test suite for UserProfile model."""
    
    def test_valid_user_profile(self):
        """Test valid user profile creation."""
        profile = UserProfile(
            id="123e4567-e89b-12d3-a456-426614174000",
            username="testuser",
            email="test@example.com",
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert profile.id == "123e4567-e89b-12d3-a456-426614174000"
        assert profile.username == "testuser"
        assert profile.email == "test@example.com"
        assert profile.is_active is True
        assert profile.is_verified is False
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)


class TestUserUpdateRequest:
    """Test suite for UserUpdateRequest model."""
    
    def test_valid_update_request(self):
        """Test valid user update request."""
        request = UserUpdateRequest(
            username="newusername",
            email="new@example.com"
        )
        
        assert request.username == "newusername"
        assert request.email == "new@example.com"
    
    def test_partial_update_request(self):
        """Test partial update request."""
        request = UserUpdateRequest(username="newusername")
        
        assert request.username == "newusername"
        assert request.email is None
    
    def test_empty_update_request(self):
        """Test empty update request."""
        request = UserUpdateRequest()
        
        assert request.username is None
        assert request.email is None
    
    def test_username_lowercase_conversion(self):
        """Test username is converted to lowercase."""
        request = UserUpdateRequest(username="NewUsername")
        
        assert request.username == "newusername"
    
    def test_invalid_username_characters(self):
        """Test username with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            UserUpdateRequest(username="invalid user!")
        
        error = exc_info.value.errors()[0]
        assert "Username can only contain" in str(error["msg"])


class TestPasswordResetRequest:
    """Test suite for PasswordResetRequest model."""
    
    def test_valid_reset_request(self):
        """Test valid password reset request."""
        request = PasswordResetRequest(email="test@example.com")
        
        assert request.email == "test@example.com"
    
    def test_invalid_email(self):
        """Test invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest(email="invalid-email")
        
        error = exc_info.value.errors()[0]
        assert error["type"] == "value_error"


class TestPasswordResetConfirm:
    """Test suite for PasswordResetConfirm model."""
    
    def test_valid_reset_confirm(self):
        """Test valid password reset confirmation."""
        request = PasswordResetConfirm(
            reset_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            new_password="NewSecurePass123!",
            confirm_password="NewSecurePass123!"
        )
        
        assert request.reset_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert request.new_password == "NewSecurePass123!"
        assert request.confirm_password == "NewSecurePass123!"
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(
                reset_token="token",
                new_password="NewSecurePass123!",
                confirm_password="DifferentPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "do not match" in str(error["msg"])
    
    def test_weak_password(self):
        """Test weak password validation."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(
                reset_token="token",
                new_password="weak",
                confirm_password="weak"
            )
        
        error = exc_info.value.errors()[0]
        assert "String should have at least 8 characters" in str(error["msg"])


class TestChangePasswordRequest:
    """Test suite for ChangePasswordRequest model."""
    
    def test_valid_change_request(self):
        """Test valid password change request."""
        request = ChangePasswordRequest(
            current_password="CurrentPass123!",
            new_password="NewSecurePass123!",
            confirm_password="NewSecurePass123!"
        )
        
        assert request.current_password == "CurrentPass123!"
        assert request.new_password == "NewSecurePass123!"
        assert request.confirm_password == "NewSecurePass123!"
    
    def test_password_mismatch(self):
        """Test new password confirmation mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="CurrentPass123!",
                new_password="NewSecurePass123!",
                confirm_password="DifferentPass123!"
            )
        
        error = exc_info.value.errors()[0]
        assert "do not match" in str(error["msg"])
    
    def test_weak_new_password(self):
        """Test weak new password validation."""
        with pytest.raises(ValidationError) as exc_info:
            ChangePasswordRequest(
                current_password="CurrentPass123!",
                new_password="weak",
                confirm_password="weak"
            )
        
        error = exc_info.value.errors()[0]
        assert "String should have at least 8 characters" in str(error["msg"])


class TestSessionManager:
    """Test suite for SessionManager class."""
    
    def test_session_manager_initialization(self):
        """Test SessionManager initialization."""
        sm = SessionManager()
        
        assert sm.secret_key is not None
        assert sm.algorithm == "HS256"
        assert sm.default_expiry_hours == 24
        assert sm.remember_expiry_hours == 24 * 30
        assert sm.password_reset_expiry_minutes == 15  # 15 minutes
    
    def test_create_session_token(self):
        """Test session token creation."""
        sm = SessionManager()
        
        token, expires_at = sm.create_session_token("user123", "testuser")
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.utcnow()
    
    def test_create_session_token_with_remember(self):
        """Test session token creation with remember flag."""
        sm = SessionManager()
        
        # Regular session
        token1, expires1 = sm.create_session_token("user123", "testuser", remember=False)
        
        # Remember me session
        token2, expires2 = sm.create_session_token("user123", "testuser", remember=True)
        
        # Remember me session should expire later
        assert expires2 > expires1
    
    def test_validate_session_token(self):
        """Test session token validation."""
        sm = SessionManager()
        
        # Create token
        token, _ = sm.create_session_token("user123", "testuser")
        
        # Validate token
        payload = sm.validate_session_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "session"
    
    def test_validate_invalid_session_token(self):
        """Test validation of invalid session token."""
        sm = SessionManager()
        
        # Test invalid token
        payload = sm.validate_session_token("invalid.token.here")
        
        assert payload is None
    
    def test_create_reset_token(self):
        """Test password reset token creation."""
        sm = SessionManager()
        
        token, expires_at = sm.create_reset_token("user123", "test@example.com")
        
        assert isinstance(token, str)
        assert len(token) > 100
        assert isinstance(expires_at, datetime)
        
        # Reset token should expire soon (15 minutes)
        expected_expiry = datetime.utcnow() + timedelta(minutes=15)
        # Allow for some time difference due to test execution
        assert abs((expires_at - expected_expiry).total_seconds()) < 120
    
    def test_validate_reset_token(self):
        """Test password reset token validation."""
        sm = SessionManager()
        
        # Create reset token
        token, _ = sm.create_reset_token("user123", "test@example.com")
        
        # Validate token
        payload = sm.validate_reset_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "password_reset"
    
    def test_validate_wrong_token_type(self):
        """Test that session tokens are rejected as reset tokens and vice versa."""
        sm = SessionManager()
        
        # Create session token
        session_token, _ = sm.create_session_token("user123", "testuser")
        
        # Create reset token
        reset_token, _ = sm.create_reset_token("user123", "test@example.com")
        
        # Session token should not validate as reset token
        assert sm.validate_reset_token(session_token) is None
        
        # Reset token should not validate as session token
        assert sm.validate_session_token(reset_token) is None
    

    
    def test_get_user_info(self):
        """Test get user info method."""
        sm = SessionManager()
        
        # Test admin user
        admin_user = sm.get_user_info("00000000-0000-0000-0000-000000000001")
        assert admin_user.id == "00000000-0000-0000-0000-000000000001"
        assert admin_user.username == "admin"
        
        # Test regular user
        regular_user = sm.get_user_info("user123")
        assert regular_user.id == "user123"
        assert regular_user.username == "user"
    
    def test_refresh_session_token(self):
        """Test session token refresh."""
        sm = SessionManager()
        
        # Create original token
        original_token, _ = sm.create_session_token("user123", "testuser")
        
        # Refresh token
        result = sm.refresh_session_token(original_token)
        
        assert result is not None
        new_token, expires_at, user = result
        
        assert isinstance(new_token, str)
        assert new_token != original_token  # Should be different
        assert isinstance(expires_at, datetime)
        assert user.id == "user123"
    
    def test_refresh_invalid_token(self):
        """Test refresh with invalid token."""
        sm = SessionManager()
        
        result = sm.refresh_session_token("invalid.token.here")
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 