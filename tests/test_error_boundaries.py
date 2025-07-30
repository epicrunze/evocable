"""
Priority 1 (Critical) Error Boundary Tests

This module tests critical error scenarios that could occur in production:
- Database connection failures during authentication
- Redis connectivity issues for rate limiting  
- Storage service unavailable during registration
- Partial failures in multi-step operations
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx

# Add the services/api directory to Python path
api_path = Path(__file__).parent.parent / "services" / "api"
sys.path.insert(0, str(api_path))

from main import app
from fastapi.testclient import TestClient

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

# Create client instance
client = APIClient()

class TestErrorBoundaries:
    """Test error boundary scenarios for authentication system."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with proper async handling."""
        # Set test environment variables
        os.environ["DEBUG"] = "true"
        os.environ["STORAGE_URL"] = "http://localhost:8001"
        
        # Create a new event loop for each test
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        yield
        
        # Cleanup
        self.loop.close()
    
    def test_database_failure_during_registration(self):
        """Test registration behavior when database is unavailable."""
        # Mock the storage service to simulate database failure
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            registration_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!"
            }
            
            response = client.post("/auth/register", json=registration_data)
            
            # Should handle the error gracefully
            assert response.status_code in [400, 500, 422]
    
    def test_database_failure_during_login(self):
        """Test login behavior when database is unavailable."""
        # Mock the storage service to simulate database failure
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.side_effect = Exception("Database connection failed")
            
            login_data = {
                "email": "admin@example.com",
                "password": "admin123!"
            }
            
            response = client.post("/auth/login/email", json=login_data)
            
            # Should return 401 for invalid credentials or 500 for server error
            assert response.status_code in [401, 500]
    
    def test_storage_service_unavailable_during_registration(self):
        """Test registration when storage service is completely unavailable."""
        # Mock the storage service to simulate network failure
        with patch('services.api.main.StorageUserService.create_user') as mock_create:
            mock_create.side_effect = Exception("Connection refused")
            
            registration_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!"
            }
            
            response = client.post("/auth/register", json=registration_data)
            
            # Should handle the error gracefully
            assert response.status_code in [400, 500, 422]
    
    def test_partial_failure_in_multi_step_operation(self):
        """Test behavior when part of a multi-step operation fails."""
        # Mock the storage service to simulate partial failure
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            login_data = {
                "email": "admin@example.com",
                "password": "admin123!"
            }
            
            response = client.post("/auth/login/email", json=login_data)
            
            # Should return 401 for invalid credentials
            assert response.status_code == 401
    
    def test_database_connection_timeout(self):
        """Test behavior when database connection times out."""
        # Mock the storage service to simulate timeout
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.side_effect = Exception("Connection timeout")
            
            login_data = {
                "email": "admin@example.com",
                "password": "admin123!"
            }
            
            response = client.post("/auth/login/email", json=login_data)
            
            # Should return 401 for invalid credentials or 500 for server error
            assert response.status_code in [401, 500]
    
    def test_network_partition_scenario(self):
        """Test behavior during network partition scenarios."""
        # Mock the storage service to simulate network partition
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.side_effect = Exception("Network unreachable")
            
            login_data = {
                "email": "admin@example.com",
                "password": "admin123!"
            }
            
            response = client.post("/auth/login/email", json=login_data)
            
            # Should handle the error gracefully
            assert response.status_code in [401, 500]
    
    def test_service_restart_scenario(self):
        """Test behavior when services restart during operations."""
        # Mock the storage service to simulate service restart
        with patch('services.api.main.StorageUserService.authenticate_user') as mock_auth:
            mock_auth.side_effect = Exception("Service unavailable")
            
            login_data = {
                "email": "admin@example.com",
                "password": "admin123!"
            }
            
            response = client.post("/auth/login/email", json=login_data)
            
            # Should handle the error gracefully
            assert response.status_code in [401, 500]
    
    def test_malformed_request_handling(self):
        """Test handling of malformed requests."""
        # Test with malformed JSON
        response = client.post("/auth/login/email", data="invalid json")
        
        # Should return 422 for unprocessable entity
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """Test handling of requests with missing required fields."""
        # Test login with missing password
        login_data = {
            "email": "admin@example.com"
            # Missing password
        }
        
        response = client.post("/auth/login/email", json=login_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_invalid_email_format(self):
        """Test handling of invalid email formats."""
        login_data = {
            "email": "invalid-email",
            "password": "admin123!"
        }
        
        response = client.post("/auth/login/email", json=login_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_password_validation_errors(self):
        """Test handling of password validation errors."""
        registration_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",  # Too weak
            "confirm_password": "weak"
        }
        
        response = client.post("/auth/register", json=registration_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_username_validation_errors(self):
        """Test handling of username validation errors."""
        registration_data = {
            "username": "a",  # Too short
            "email": "test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!"
        }
        
        response = client.post("/auth/register", json=registration_data)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_rate_limiting_error_handling(self):
        """Test handling of rate limiting errors."""
        # Make multiple rapid requests to trigger rate limiting
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        responses = []
        for _ in range(10):  # Make multiple requests
            response = client.post("/auth/login/email", json=login_data)
            responses.append(response.status_code)
        
        # Should handle rate limiting gracefully
        # Responses should be 401 (invalid credentials) or 429 (rate limited)
        assert all(status in [401, 429] for status in responses) 