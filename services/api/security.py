"""Security utilities for authentication and password management."""

import secrets
import string
import re
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from passlib.hash import bcrypt
from datetime import datetime, timedelta


# Password hashing context - uses bcrypt with adaptive rounds
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Adaptive cost factor for bcrypt
)


class PasswordValidator:
    """Validates password strength according to security requirements."""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    # Regex patterns for password requirements
    PATTERNS = {
        'uppercase': r'[A-Z]',
        'lowercase': r'[a-z]', 
        'digit': r'\d',
        'special': r'[!@#$%^&*(),.?":{}|<>]'
    }
    
    REQUIREMENTS = {
        'uppercase': 'at least one uppercase letter',
        'lowercase': 'at least one lowercase letter',
        'digit': 'at least one number',
        'special': 'at least one special character (!@#$%^&*(),.?":{}|<>)'
    }
    
    @classmethod
    def validate_password(cls, password: str) -> Dict[str, Any]:
        """
        Validate password strength and return detailed results.
        
        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []
        
        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        elif len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be no more than {cls.MAX_LENGTH} characters long")
        
        # Check character requirements
        for requirement, pattern in cls.PATTERNS.items():
            if not re.search(pattern, password):
                errors.append(f"Password must contain {cls.REQUIREMENTS[requirement]}")
        
        # Check for common weak patterns
        if password.lower() in cls._get_common_passwords():
            errors.append("Password is too common - please choose a stronger password")
        
        # Check for repeated characters (more than 3 in a row)
        if re.search(r'(.)\1{3,}', password):
            errors.append("Password cannot contain more than 3 consecutive identical characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'strength_score': cls._calculate_strength_score(password)
        }
    
    @classmethod
    def _calculate_strength_score(cls, password: str) -> int:
        """Calculate password strength score (0-100)."""
        score = 0
        
        # Length bonus
        score += min(len(password) * 2, 25)
        
        # Character variety bonus
        if re.search(cls.PATTERNS['lowercase'], password):
            score += 15
        if re.search(cls.PATTERNS['uppercase'], password):
            score += 15
        if re.search(cls.PATTERNS['digit'], password):
            score += 15
        if re.search(cls.PATTERNS['special'], password):
            score += 20
        
        # Entropy bonus for non-dictionary words
        unique_chars = len(set(password.lower()))
        score += min(unique_chars * 2, 10)
        
        return min(score, 100)
    
    @classmethod
    def _get_common_passwords(cls) -> set:
        """Return set of common passwords to reject."""
        return {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'login', 'master', 'hello', 'freedom'
        }


class PasswordHasher:
    """Handles secure password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with salt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Validate password before hashing
        validation = PasswordValidator.validate_password(password)
        if not validation['valid']:
            raise ValueError(f"Password validation failed: {'; '.join(validation['errors'])}")
        
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        if not plain_password or not hashed_password:
            return False
        
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            # Hash format is invalid or corrupted
            return False
    
    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """
        Check if a password hash needs to be updated.
        
        This is useful when bcrypt cost factor is increased.
        
        Args:
            hashed_password: Stored password hash
            
        Returns:
            True if hash should be updated
        """
        try:
            return pwd_context.needs_update(hashed_password)
        except Exception:
            return True  # If we can't parse it, it needs updating


class TokenGenerator:
    """Generates secure tokens for various purposes."""
    
    @staticmethod
    def generate_reset_token(length: int = 32) -> str:
        """
        Generate a secure token for password reset.
        
        Args:
            length: Token length (default 32 characters)
            
        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_verification_token(length: int = 24) -> str:
        """
        Generate a secure token for email verification.
        
        Args:
            length: Token length (default 24 characters)
            
        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key(length: int = 32) -> str:
        """
        Generate a secure API key.
        
        Args:
            length: Key length (default 32 characters)
            
        Returns:
            Hex-encoded random key
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_secure_filename(original_filename: str, length: int = 16) -> str:
        """
        Generate a secure filename with random prefix.
        
        Args:
            original_filename: Original file name
            length: Random prefix length
            
        Returns:
            Secure filename with random prefix
        """
        secure_prefix = secrets.token_hex(length // 2)
        # Sanitize original filename
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', original_filename)
        return f"{secure_prefix}_{safe_filename}"


class SecurityUtils:
    """Additional security utilities."""
    
    @staticmethod
    def is_safe_redirect(url: str, allowed_hosts: list = None) -> bool:
        """
        Check if a redirect URL is safe to prevent open redirect attacks.
        
        Args:
            url: URL to validate
            allowed_hosts: List of allowed host names
            
        Returns:
            True if URL is safe for redirect
        """
        if not url:
            return False
        
        # Relative URLs are generally safe
        if url.startswith('/') and not url.startswith('//'):
            return True
        
        # Check against allowed hosts if provided
        if allowed_hosts:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc in allowed_hosts
            except Exception:
                return False
        
        # By default, only allow relative URLs
        return False
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Sanitize and normalize email address.
        
        Args:
            email: Email address to sanitize
            
        Returns:
            Normalized email address
        """
        if not email:
            return ""
        
        # Convert to lowercase and strip whitespace
        email = email.lower().strip()
        
        # Basic email format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise ValueError("Invalid email format")
        
        return email
    
    @staticmethod
    def sanitize_username(username: str) -> str:
        """
        Sanitize username for safe storage and display.
        
        Args:
            username: Username to sanitize
            
        Returns:
            Sanitized username
        """
        if not username:
            return ""
        
        # Remove whitespace and convert to lowercase
        username = username.strip().lower()
        
        # Only allow alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        
        # Check length
        if len(username) < 3 or len(username) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        
        return username


# Convenience functions for backward compatibility
def hash_password(password: str) -> str:
    """Hash a password - convenience function."""
    return PasswordHasher.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password - convenience function."""
    return PasswordHasher.verify_password(plain_password, hashed_password)


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength - convenience function."""
    return PasswordValidator.validate_password(password) 