"""Tests for security utilities."""

import pytest
import secrets
import re
from unittest.mock import patch

# Import our security modules
from security import (
    PasswordValidator, PasswordHasher, TokenGenerator, SecurityUtils,
    hash_password, verify_password, validate_password_strength
)


class TestPasswordValidator:
    """Test suite for PasswordValidator."""
    
    def test_valid_strong_password(self):
        """Test validation of strong password."""
        result = PasswordValidator.validate_password("StrongPass123!")
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['strength_score'] >= 80
    
    def test_password_too_short(self):
        """Test password length validation."""
        result = PasswordValidator.validate_password("Short1!")
        
        assert result['valid'] is False
        assert any("at least 8 characters" in error for error in result['errors'])
    
    def test_password_too_long(self):
        """Test maximum password length."""
        long_password = "a" * 150  # Over 128 character limit
        result = PasswordValidator.validate_password(long_password)
        
        assert result['valid'] is False
        assert any("no more than 128 characters" in error for error in result['errors'])
    
    def test_password_missing_uppercase(self):
        """Test password without uppercase letter."""
        result = PasswordValidator.validate_password("lowercase123!")
        
        assert result['valid'] is False
        assert any("uppercase letter" in error for error in result['errors'])
    
    def test_password_missing_lowercase(self):
        """Test password without lowercase letter."""
        result = PasswordValidator.validate_password("UPPERCASE123!")
        
        assert result['valid'] is False
        assert any("lowercase letter" in error for error in result['errors'])
    
    def test_password_missing_digit(self):
        """Test password without digit."""
        result = PasswordValidator.validate_password("NoDigitsHere!")
        
        assert result['valid'] is False
        assert any("one number" in error for error in result['errors'])
    
    def test_password_missing_special_char(self):
        """Test password without special character."""
        result = PasswordValidator.validate_password("NoSpecialChar123")
        
        assert result['valid'] is False
        assert any("special character" in error for error in result['errors'])
    
    def test_common_password_rejection(self):
        """Test rejection of common passwords."""
        result = PasswordValidator.validate_password("password")
        
        assert result['valid'] is False
        assert any("too common" in error for error in result['errors'])
    
    def test_repeated_characters(self):
        """Test rejection of passwords with too many repeated characters."""
        result = PasswordValidator.validate_password("Aaaaa1234!")
        
        assert result['valid'] is False
        assert any("consecutive identical characters" in error for error in result['errors'])
    
    def test_strength_score_calculation(self):
        """Test password strength score calculation."""
        # Test different strength levels
        weak_score = PasswordValidator.validate_password("password")['strength_score']
        medium_score = PasswordValidator.validate_password("Password1")['strength_score']
        strong_score = PasswordValidator.validate_password("StrongP@ssw0rd123!")['strength_score']
        
        assert weak_score < medium_score < strong_score
        assert strong_score >= 80  # Strong passwords should score high


class TestPasswordHasher:
    """Test suite for PasswordHasher."""
    
    def test_hash_password_success(self):
        """Test successful password hashing."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith('$2b$')  # Bcrypt prefix
        assert hashed != password  # Should be different from original
    
    def test_hash_empty_password(self):
        """Test hashing empty password raises error."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordHasher.hash_password("")
    
    def test_hash_weak_password(self):
        """Test hashing weak password raises error."""
        with pytest.raises(ValueError, match="Password validation failed"):
            PasswordHasher.hash_password("weak")
    
    def test_verify_password_correct(self):
        """Test verification of correct password."""
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)
        
        assert PasswordHasher.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verification of incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordHasher.hash_password(password)
        
        assert PasswordHasher.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_inputs(self):
        """Test verification with empty inputs."""
        assert PasswordHasher.verify_password("", "hash") is False
        assert PasswordHasher.verify_password("password", "") is False
        assert PasswordHasher.verify_password("", "") is False
    
    def test_verify_password_invalid_hash(self):
        """Test verification with invalid hash format."""
        assert PasswordHasher.verify_password("password", "invalid_hash") is False
    
    def test_needs_rehash(self):
        """Test hash rehashing detection."""
        # Create a hash
        password = "TestPassword123!"
        hashed = PasswordHasher.hash_password(password)
        
        # Fresh hash shouldn't need rehashing
        assert PasswordHasher.needs_rehash(hashed) is False
        
        # Invalid hash should need rehashing
        assert PasswordHasher.needs_rehash("invalid_hash") is True


class TestTokenGenerator:
    """Test suite for TokenGenerator."""
    
    def test_generate_reset_token(self):
        """Test reset token generation."""
        token = TokenGenerator.generate_reset_token()
        
        assert token is not None
        assert len(token) > 20  # Should be reasonably long
        assert isinstance(token, str)
        
        # Test custom length
        custom_token = TokenGenerator.generate_reset_token(length=16)
        assert len(custom_token) >= 16  # URL-safe encoding may vary length slightly
    
    def test_generate_verification_token(self):
        """Test verification token generation."""
        token = TokenGenerator.generate_verification_token()
        
        assert token is not None
        assert len(token) > 15  # Should be reasonably long
        assert isinstance(token, str)
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = TokenGenerator.generate_api_key()
        
        assert api_key is not None
        assert len(api_key) >= 32  # Should be at least 32 chars
        assert isinstance(api_key, str)
        # Should be hex characters only
        assert all(c in '0123456789abcdef' for c in api_key)
    
    def test_generate_secure_filename(self):
        """Test secure filename generation."""
        original = "test_file.txt"
        secure = TokenGenerator.generate_secure_filename(original)
        
        assert secure != original
        assert "test_file.txt" in secure  # Should contain original name
        assert "_" in secure  # Should have separator
        assert len(secure) > len(original)  # Should be longer
    
    def test_token_uniqueness(self):
        """Test that generated tokens are unique."""
        tokens = [TokenGenerator.generate_reset_token() for _ in range(10)]
        
        # All tokens should be unique
        assert len(set(tokens)) == len(tokens)


class TestSecurityUtils:
    """Test suite for SecurityUtils."""
    
    def test_sanitize_email_valid(self):
        """Test email sanitization with valid email."""
        result = SecurityUtils.sanitize_email("TEST@EXAMPLE.COM")
        assert result == "test@example.com"
        
        result = SecurityUtils.sanitize_email("  user@domain.org  ")
        assert result == "user@domain.org"
    
    def test_sanitize_email_invalid(self):
        """Test email sanitization with invalid email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            SecurityUtils.sanitize_email("invalid-email")
        
        with pytest.raises(ValueError, match="Invalid email format"):
            SecurityUtils.sanitize_email("@domain.com")
    
    def test_sanitize_email_empty(self):
        """Test email sanitization with empty input."""
        result = SecurityUtils.sanitize_email("")
        assert result == ""
    
    def test_sanitize_username_valid(self):
        """Test username sanitization with valid username."""
        result = SecurityUtils.sanitize_username("TestUser_123")
        assert result == "testuser_123"
        
        result = SecurityUtils.sanitize_username("  ValidUser-Name  ")
        assert result == "validuser-name"
    
    def test_sanitize_username_invalid_chars(self):
        """Test username sanitization with invalid characters."""
        with pytest.raises(ValueError, match="Username can only contain"):
            SecurityUtils.sanitize_username("invalid user!")
        
        with pytest.raises(ValueError, match="Username can only contain"):
            SecurityUtils.sanitize_username("user@name")
    
    def test_sanitize_username_invalid_length(self):
        """Test username sanitization with invalid length."""
        with pytest.raises(ValueError, match="between 3 and 50 characters"):
            SecurityUtils.sanitize_username("ab")  # Too short
        
        with pytest.raises(ValueError, match="between 3 and 50 characters"):
            SecurityUtils.sanitize_username("a" * 51)  # Too long
    
    def test_sanitize_username_empty(self):
        """Test username sanitization with empty input."""
        result = SecurityUtils.sanitize_username("")
        assert result == ""
    
    def test_is_safe_redirect_relative_url(self):
        """Test safe redirect detection for relative URLs."""
        assert SecurityUtils.is_safe_redirect("/dashboard") is True
        assert SecurityUtils.is_safe_redirect("/api/books") is True
        assert SecurityUtils.is_safe_redirect("//evil.com") is False  # Protocol-relative
    
    def test_is_safe_redirect_with_allowed_hosts(self):
        """Test safe redirect with allowed hosts."""
        allowed_hosts = ["example.com", "subdomain.example.com"]
        
        # Should allow URLs from allowed hosts
        assert SecurityUtils.is_safe_redirect(
            "https://example.com/path", allowed_hosts
        ) is True
        
        # Should reject URLs from other hosts
        assert SecurityUtils.is_safe_redirect(
            "https://evil.com/path", allowed_hosts
        ) is False
    
    def test_is_safe_redirect_no_url(self):
        """Test safe redirect with empty URL."""
        assert SecurityUtils.is_safe_redirect("") is False
        assert SecurityUtils.is_safe_redirect(None) is False


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_hash_password_convenience(self):
        """Test convenience hash_password function."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed.startswith('$2b$')
    
    def test_verify_password_convenience(self):
        """Test convenience verify_password function."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_validate_password_strength_convenience(self):
        """Test convenience validate_password_strength function."""
        result = validate_password_strength("StrongPassword123!")
        
        assert 'valid' in result
        assert 'errors' in result
        assert 'strength_score' in result


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    def test_complete_password_workflow(self):
        """Test complete password creation and verification workflow."""
        # 1. Validate password strength
        password = "SecurePassword123!"
        validation = validate_password_strength(password)
        assert validation['valid'] is True
        
        # 2. Hash the password
        hashed = hash_password(password)
        assert hashed is not None
        
        # 3. Verify the password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_user_input_sanitization(self):
        """Test complete user input sanitization."""
        # Sanitize email
        email = SecurityUtils.sanitize_email("  TEST@Example.COM  ")
        assert email == "test@example.com"
        
        # Sanitize username
        username = SecurityUtils.sanitize_username("  TestUser_123  ")
        assert username == "testuser_123"
        
        # Both should be valid for user creation
        assert "@" in email
        assert len(username) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 