"""Tests for Phase 2 authentication endpoints."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx
import os

# Test client that connects to actual running API service
class APIClient:
    """Client for connecting to the actual running API service."""
    
    def __init__(self, base_url=None):
        # Read from environment variable, fallback to Docker service name
        if base_url is None:
            base_url = os.environ.get("API_BASE_URL", "http://api:8000")
        self.base_url = base_url
        self.client = httpx.Client(verify=False, timeout=30.0)
    
    def post(self, endpoint, **kwargs):
        """Make POST request to API."""
        url = f"{self.base_url}{endpoint}"
        return self.client.post(url, **kwargs)
    
    def get(self, endpoint, **kwargs):
        """Make GET request to API."""
        url = f"{self.base_url}{endpoint}"
        return self.client.get(url, **kwargs)
    
    def put(self, endpoint, **kwargs):
        """Make PUT request to API."""
        url = f"{self.base_url}{endpoint}"
        return self.client.put(url, **kwargs)
    
    def delete(self, endpoint, **kwargs):
        """Make DELETE request to API."""
        url = f"{self.base_url}{endpoint}"
        return self.client.delete(url, **kwargs)

class TestPhase2AuthenticationEndpoints:
    """Test suite for Phase 2 authentication endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client that connects to actual API service."""
        return APIClient()
    
    def get_admin_token(self, client):
        """Get admin token for testing."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        login_response = client.post("/auth/login/email", json=login_data)
        
        if login_response.status_code == 200:
            return login_response.json()["sessionToken"]
        else:
            raise Exception(f"Could not get admin token: {login_response.status_code} - {login_response.text}")
    
    def test_register_endpoint_structure(self, client):
        """Test user registration endpoint structure."""
        # Valid registration request with unique identifiers
        import time
        unique_suffix = str(int(time.time() * 1000))  # More unique with milliseconds
        register_data = {
            "username": f"testuser{unique_suffix}",
            "email": f"test{unique_suffix}@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }
        
        response = client.post("/auth/register", json=register_data)
        
        # Should return 201 Created for successful registration
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["username"] == f"testuser{unique_suffix}"
        assert data["email"] == f"test{unique_suffix}@example.com"
    
    def test_register_validation_errors(self, client):
        """Test registration validation errors."""
        # Test weak password
        weak_password_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak"
        }
        
        response = client.post("/auth/register", json=weak_password_data)
        
        # Should return validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Test password mismatch
        mismatch_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = client.post("/auth/register", json=mismatch_data)
        assert response.status_code == 422
    
    def test_register_invalid_username(self, client):
        """Test registration with invalid username."""
        invalid_username_data = {
            "username": "invalid user!",  # Contains space and special char
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }
        
        response = client.post("/auth/register", json=invalid_username_data)
        assert response.status_code == 422
        
        data = response.json()
        error_msg = str(data["detail"])
        assert "Username can only contain" in error_msg
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        invalid_email_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!"
        }
        
        response = client.post("/auth/register", json=invalid_email_data)
        assert response.status_code == 422
    
    def test_login_email_endpoint_structure(self, client):
        """Test email login endpoint structure."""
        login_data = {
            "email": "admin@example.com",  # Use correct admin email
            "password": "admin123!",  # Use default admin password
            "remember": False
        }
        
        response = client.post("/auth/login/email", json=login_data)
        
        # Should return 200 OK for successful login
        assert response.status_code == 200
        data = response.json()
        assert "sessionToken" in data
        assert "expiresAt" in data
        assert "user" in data
    
    def test_login_email_validation(self, client):
        """Test email login validation."""
        # Test invalid email
        invalid_data = {
            "email": "invalid-email",
            "password": "TestPassword123!"
        }
        
        response = client.post("/auth/login/email", json=invalid_data)
        assert response.status_code == 422
        
        # Test missing password
        missing_password = {
            "email": "test@example.com"
        }
        
        response = client.post("/auth/login/email", json=missing_password)
        assert response.status_code == 422
    
    def test_login_email_remember_me(self, client):
        """Test email login with remember me."""
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "remember": True
        }
        
        response = client.post("/auth/login/email", json=login_data)
        
        # Should return 200 OK for successful login with remember me
        assert response.status_code == 200
    
    def test_get_profile_endpoint(self, client):
        """Test get user profile endpoint."""
        # Test without authentication
        response = client.get("/auth/profile")
        assert response.status_code == 403  # API returns 403 for missing auth, not 401
        
        # Test with proper JWT authentication - first login to get a token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!",
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["sessionToken"]
        
        # Test with valid JWT token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/profile", headers=headers)
        
        # Should return 200 OK for successful profile retrieval
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
    
    def test_update_profile_endpoint(self, client):
        """Test update user profile endpoint."""
        # Test without authentication
        update_data = {"email": "newemail@example.com"}
        response = client.put("/auth/profile", json=update_data)
        assert response.status_code == 403  # API returns 403 for missing auth, not 401
        
        # Test with valid JWT token using shared helper
        token = self.get_admin_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {"email": "newemail@example.com"}
        response = client.put("/auth/profile", json=update_data, headers=headers)
        
        # Should return 200 OK for successful profile update
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
    
    def test_update_profile_validation(self, client):
        """Test profile update validation."""
        # First login to get a valid JWT token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!",
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["sessionToken"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test invalid username
        invalid_data = {
            "username": "invalid user!"
        }
        
        response = client.put("/auth/profile", json=invalid_data, headers=headers)
        assert response.status_code == 422
        
        # Test invalid email
        invalid_email_data = {
            "email": "invalid-email"
        }
        
        response = client.put("/auth/profile", json=invalid_email_data, headers=headers)
        assert response.status_code == 422
    
    def test_change_password_endpoint(self, client):
        """Test change password endpoint."""
        password_data = {
            "current_password": "admin123!",  # Use actual admin password
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        # Test without authentication
        response = client.post("/auth/change-password", json=password_data)
        assert response.status_code == 403  # API returns 403 for missing auth, not 401
        
        # Test with valid JWT token using shared helper
        token = self.get_admin_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/auth/change-password", json=password_data, headers=headers)
        
        # Should return 200 OK for successful password change
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Reset password back to original for other tests
        reset_password_data = {
            "current_password": "NewPassword123!",  # Now using the new password
            "new_password": "admin123!",
            "confirm_password": "admin123!"
        }
        # Get a new token since password changed
        login_data = {
            "email": "admin@example.com",
            "password": "NewPassword123!",  # Use new password to login
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        if login_response.status_code == 200:
            new_token = login_response.json()["sessionToken"]
            new_headers = {"Authorization": f"Bearer {new_token}"}
            # Reset password back
            client.post("/auth/change-password", json=reset_password_data, headers=new_headers)
    
    def test_change_password_validation(self, client):
        """Test change password validation."""
        # First login to get a valid JWT token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!",
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["sessionToken"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test weak new password
        weak_password_data = {
            "current_password": "admin123!",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = client.post("/auth/change-password", json=weak_password_data, headers=headers)
        assert response.status_code == 422
        
        # Test password mismatch
        mismatch_data = {
            "current_password": "admin123!",
            "new_password": "NewPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = client.post("/auth/change-password", json=mismatch_data, headers=headers)
        assert response.status_code == 422
    
    def test_forgot_password_endpoint(self, client):
        """Test forgot password endpoint."""
        reset_data = {
            "email": "test@example.com"
        }
        
        response = client.post("/auth/forgot-password", json=reset_data)
        
        # Should return success message (placeholder implementation)
        assert response.status_code == 200
        data = response.json()
        assert "reset link has been sent" in data["message"]
    
    def test_forgot_password_validation(self, client):
        """Test forgot password validation."""
        # Test invalid email
        invalid_data = {
            "email": "invalid-email"
        }
        
        response = client.post("/auth/forgot-password", json=invalid_data)
        assert response.status_code == 422
    
    def test_reset_password_endpoint(self, client):
        """Test reset password endpoint."""
        reset_data = {
            "reset_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "new_password": "NewSecurePass123!",
            "confirm_password": "NewSecurePass123!"
        }
        
        response = client.post("/auth/reset-password", json=reset_data)
        
        # Should return 400 Bad Request for invalid token
        assert response.status_code == 400
        data = response.json()
        assert "Invalid or expired reset token" in data["detail"]
    
    def test_reset_password_validation(self, client):
        """Test reset password validation."""
        # Test weak password
        weak_password_data = {
            "reset_token": "token",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = client.post("/auth/reset-password", json=weak_password_data)
        assert response.status_code == 422
        
        # Test password mismatch
        mismatch_data = {
            "reset_token": "token",
            "new_password": "NewSecurePass123!",
            "confirm_password": "DifferentPass123!"
        }
        
        response = client.post("/auth/reset-password", json=mismatch_data)
        assert response.status_code == 422
    

    
    def test_logout_endpoint_still_works(self, client):
        """Test that logout endpoint still works."""
        # First login to get a valid JWT token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!",
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["sessionToken"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/auth/logout", headers=headers)
        
        # Logout should work
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out" in data["message"]
    
    def test_refresh_endpoint_still_works(self, client):
        """Test that refresh endpoint still works."""
        # First login to get a valid JWT token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!",
            "remember": False
        }
        login_response = client.post("/auth/login/email", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["sessionToken"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/auth/refresh", headers=headers)
        
        # Refresh should work
        assert response.status_code == 200
        data = response.json()
        assert "sessionToken" in data


class TestPhase2APIDocumentation:
    """Test API documentation for Phase 2 endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        # Add the services/api directory to the path for importing
        import sys
        from pathlib import Path
        
        # Add services/api to path for imports
        api_path = Path(__file__).parent.parent / "services" / "api"
        sys.path.insert(0, str(api_path))
        
        with patch('services.storage.user_service.UserService'), \
             patch('services.api.auth_models.SessionManager'), \
             patch('services.storage.book_service.BookService'), \
             patch('services.api.main.redis_client'), \
             patch('services.api.main.http_client'):
            
            from services.api.main import app
            return APIClient()
    
    def test_openapi_schema_includes_new_endpoints(self, client):
        """Test that OpenAPI schema includes all new endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        paths = schema["paths"]
        
        # Check all new endpoints are documented
        assert "/auth/register" in paths
        assert "/auth/login/email" in paths
        assert "/auth/profile" in paths
        assert "/auth/change-password" in paths
        assert "/auth/forgot-password" in paths
        assert "/auth/reset-password" in paths
        
        # Check HTTP methods
        assert "post" in paths["/auth/register"]
        assert "post" in paths["/auth/login/email"]
        assert "get" in paths["/auth/profile"]
        assert "put" in paths["/auth/profile"]
        assert "post" in paths["/auth/change-password"]
        assert "post" in paths["/auth/forgot-password"]
        assert "post" in paths["/auth/reset-password"]
    
    def test_endpoint_tags(self, client):
        """Test that endpoints are properly tagged."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]
        
        # All auth endpoints should be tagged as "Authentication"
        auth_endpoints = [
            "/auth/register",
            "/auth/login/email", 
            "/auth/profile",
            "/auth/change-password",
            "/auth/forgot-password",
            "/auth/reset-password"
        ]
        
        for endpoint in auth_endpoints:
            if endpoint in paths:
                for method in paths[endpoint]:
                    if "tags" in paths[endpoint][method]:
                        assert "Authentication" in paths[endpoint][method]["tags"]
    
    def test_request_response_schemas(self, client):
        """Test that request/response schemas are properly defined."""
        response = client.get("/openapi.json")
        schema = response.json()
        components = schema.get("components", {})
        schemas = components.get("schemas", {})
        
        # Check that our new models are in the schema
        expected_schemas = [
            "RegisterRequest",
            "NewLoginRequest", 
            "UserProfile",
            "UserUpdateRequest",
            "PasswordResetRequest",
            "PasswordResetConfirm",
            "ChangePasswordRequest"
        ]
        
        for schema_name in expected_schemas:
            # Note: FastAPI may modify schema names, so we check for variations
            found = any(schema_name in key for key in schemas.keys())
            assert found, f"Schema {schema_name} not found in API documentation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 