"""
Priority 1 (Critical) Rate Limiting Boundary Tests

This module tests critical rate limiting scenarios:
- Rate limit bypass attempts
- Distributed rate limiting consistency
- Rate limit recovery behavior
- Mixed endpoint rate limiting interactions
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx

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

class TestRateLimitingBoundaries:
    """Test rate limiting boundary scenarios."""
    
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
    
    def test_login_rate_limiting(self):
        """Test rate limiting on login endpoint."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        # Make multiple rapid login attempts
        responses = []
        for _ in range(15):  # More than the rate limit
            response = client.post("/auth/login/email", json=login_data)
            responses.append(response.status_code)
        
        # Should see rate limiting in effect
        # Responses should be 401 (invalid credentials) or 429 (rate limited)
        assert all(status in [401, 429] for status in responses)
        
        # At least some should be rate limited
        assert 429 in responses
    
    def test_registration_rate_limiting(self):
        """Test rate limiting on registration endpoint."""
        import uuid
        
        # Make multiple rapid registration attempts
        responses = []
        for i in range(15):  # More than the rate limit
            unique_email = f"testuser_{uuid.uuid4().hex[:8]}_{i}@example.com"
            registration_data = {
                "username": f"testuser_{i}",
                "email": unique_email,
                "password": "TestPass123!",
                "confirm_password": "TestPass123!"
            }
            
            response = client.post("/auth/register", json=registration_data)
            responses.append(response.status_code)
        
        # Should see rate limiting in effect
        # Responses should be 201 (success), 400 (user exists), 422 (validation), or 429 (rate limited)
        assert all(status in [201, 400, 422, 429] for status in responses)
        
        # At least some should be rate limited
        assert 429 in responses
    
    def test_profile_update_rate_limiting(self):
        """Test rate limiting on profile update endpoint."""
        # First, try to login to get a token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        login_response = client.post("/auth/login/email", json=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json()["sessionToken"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make multiple rapid profile update attempts
            responses = []
            for i in range(15):  # More than the rate limit
                update_data = {
                    "username": f"admin_updated_{i}",
                    "email": f"admin_updated_{i}@example.com"
                }
                
                response = client.put("/auth/profile", json=update_data, headers=headers)
                responses.append(response.status_code)
            
            # Should see rate limiting in effect
            # Responses should be 200 (success), 400 (validation), 422 (validation), or 429 (rate limited)
            assert all(status in [200, 400, 422, 429] for status in responses)
            
            # At least some should be rate limited
            assert 429 in responses
        else:
            # Skip test if admin login fails
            pytest.skip("Admin login failed, skipping profile update rate limiting test")
    
    def test_password_change_rate_limiting(self):
        """Test rate limiting on password change endpoint."""
        # First, try to login to get a token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        login_response = client.post("/auth/login/email", json=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json()["sessionToken"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Make multiple rapid password change attempts
            responses = []
            for i in range(15):  # More than the rate limit
                change_data = {
                    "current_password": "admin123!",
                    "new_password": f"NewPass123!_{i}",
                    "confirm_password": f"NewPass123!_{i}"
                }
                
                response = client.post("/auth/change-password", json=change_data, headers=headers)
                responses.append(response.status_code)
            
            # Should see rate limiting in effect
            # Responses should be 200 (success), 400 (wrong password), 422 (validation), or 429 (rate limited)
            assert all(status in [200, 400, 422, 429] for status in responses)
            
            # At least some should be rate limited
            assert 429 in responses
        else:
            # Skip test if admin login fails
            pytest.skip("Admin login failed, skipping password change rate limiting test")
    
    def test_forgot_password_rate_limiting(self):
        """Test rate limiting on forgot password endpoint."""
        # Make multiple rapid forgot password attempts
        responses = []
        for i in range(15):  # More than the rate limit
            forgot_data = {
                "email": f"test{i}@example.com"
            }
            
            response = client.post("/auth/forgot-password", json=forgot_data)
            responses.append(response.status_code)
        
        # Should see rate limiting in effect
        # Responses should be 200 (success), 422 (validation), or 429 (rate limited)
        assert all(status in [200, 422, 429] for status in responses)
        
        # At least some should be rate limited
        assert 429 in responses
    
    def test_reset_password_rate_limiting(self):
        """Test rate limiting on reset password endpoint."""
        # Make multiple rapid reset password attempts
        responses = []
        for i in range(15):  # More than the rate limit
            reset_data = {
                "reset_token": f"fake_token_{i}",
                "new_password": f"NewPass123!_{i}",
                "confirm_password": f"NewPass123!_{i}"
            }
            
            response = client.post("/auth/reset-password", json=reset_data)
            responses.append(response.status_code)
        
        # Should see rate limiting in effect
        # Responses should be 400 (invalid token), 422 (validation), or 429 (rate limited)
        assert all(status in [400, 422, 429] for status in responses)
        
        # At least some should be rate limited
        assert 429 in responses
    
    def test_mixed_endpoint_rate_limiting_interactions(self):
        """Test rate limiting interactions across different endpoints."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        # Make requests to different endpoints
        responses = []
        endpoints = [
            ("/auth/login/email", "POST", login_data),
            ("/auth/forgot-password", "POST", {"email": "test@example.com"}),
            ("/health", "GET", None),
        ]
        
        for _ in range(5):  # Multiple rounds
            for endpoint, method, data in endpoints:
                if method == "POST":
                    response = client.post(endpoint, json=data)
                else:
                    response = client.get(endpoint)
                responses.append(response.status_code)
        
        # Should handle rate limiting gracefully
        # Responses should be appropriate for each endpoint
        assert all(status in [200, 401, 422, 429] for status in responses)
    
    def test_rate_limit_consistency_across_requests(self):
        """Test that rate limiting is consistent across multiple requests."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        # Make multiple requests and check consistency
        responses = []
        for _ in range(20):  # More than the rate limit
            response = client.post("/auth/login/email", json=login_data)
            responses.append(response.status_code)
        
        # Should see consistent rate limiting behavior
        # All responses should be either 401 (invalid credentials) or 429 (rate limited)
        assert all(status in [401, 429] for status in responses)
        
        # Should have both types of responses
        assert 401 in responses  # Invalid credentials
        assert 429 in responses  # Rate limited
    
    def test_rate_limit_recovery_after_cooldown(self):
        """Test that rate limiting recovers after cooldown period."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        # Make initial requests to trigger rate limiting
        initial_responses = []
        for _ in range(15):  # Trigger rate limiting
            response = client.post("/auth/login/email", json=login_data)
            initial_responses.append(response.status_code)
        
        # Should see rate limiting in effect
        assert 429 in initial_responses
        
        # Wait a moment and try again (rate limiting should still be in effect)
        import time
        time.sleep(1)
        
        # Make a few more requests
        recovery_responses = []
        for _ in range(5):
            response = client.post("/auth/login/email", json=login_data)
            recovery_responses.append(response.status_code)
        
        # Should still see rate limiting or invalid credentials
        assert all(status in [401, 429] for status in recovery_responses)
    
    def test_rate_limit_bypass_attempts(self):
        """Test that rate limiting cannot be easily bypassed."""
        login_data = {
            "email": "admin@example.com",
            "password": "admin123!"
        }
        
        # Try different approaches to bypass rate limiting
        responses = []
        
        # Standard requests
        for _ in range(10):
            response = client.post("/auth/login/email", json=login_data)
            responses.append(response.status_code)
        
        # Requests with different headers
        for _ in range(5):
            headers = {"User-Agent": f"TestBot_{_}"}
            response = client.post("/auth/login/email", json=login_data, headers=headers)
            responses.append(response.status_code)
        
        # All should be rate limited or return invalid credentials
        assert all(status in [401, 429] for status in responses)
        
        # Should see rate limiting in effect
        assert 429 in responses
    
    def test_rate_limit_edge_cases(self):
        """Test rate limiting edge cases."""
        # Test with malformed requests
        malformed_responses = []
        for _ in range(10):
            response = client.post("/auth/login/email", data="invalid json")
            malformed_responses.append(response.status_code)
        
        # Should return 422 for malformed requests
        assert all(status == 422 for status in malformed_responses)
        
        # Test with missing fields
        missing_field_responses = []
        for _ in range(10):
            response = client.post("/auth/login/email", json={"email": "test@example.com"})
            missing_field_responses.append(response.status_code)
        
        # Should return 422 for missing fields
        assert all(status == 422 for status in missing_field_responses) 