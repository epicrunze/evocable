#!/usr/bin/env python3
"""Test runner for Audiobook Server API tests."""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

def setup_test_environment():
    """Set up test environment variables."""
    # Load environment variables from .env file if it exists
    env_file_path = Path(__file__).parent.parent / ".env"
    try:
        with open(env_file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ.setdefault(key, value)
    except Exception as e:
        print(f"⚠️  Could not load .env file: {e}")
    
    # Check if we're running inside Docker network
    import socket
    try:
        socket.create_connection(("redis", 6379), timeout=1)
        # We're inside Docker network
        redis_url = "redis://redis:6379"
        storage_url = "http://storage:8001"
        # Use proper HTTPS URL for API that matches nginx config
        api_url = "https://server.epicrunze.com" 
    except (socket.error, OSError):
        # We're outside Docker network, try localhost with proper HTTPS
        try:
            socket.create_connection(("localhost", 6379), timeout=1)
            redis_url = "redis://localhost:6379"
            storage_url = "http://localhost:8001"
            # Use proper HTTPS URL that matches nginx config
            api_url = "https://server.epicrunze.com"
        except (socket.error, OSError):
            # Redis not available, use mock or skip Redis-dependent tests
            print("⚠️  Redis not available. Some tests may be skipped.")
            redis_url = "redis://localhost:6379"  # Will fail gracefully
            storage_url = "http://localhost:8001"
            # Use proper HTTPS URL that matches nginx config
            api_url = "https://server.epicrunze.com"
    
    os.environ.update({
        "SECRET_KEY": "test-jwt-secret-key-change-in-production",
        "DATABASE_PATH": "/tmp/test_audiobooks.db",
        "DATABASE_URL": "sqlite:///:memory:",  # Use in-memory database for testing
        "REDIS_URL": redis_url,
        "STORAGE_URL": storage_url,
        "INGEST_URL": "http://ingest:8002" if "redis" in redis_url else "http://localhost:8002", 
        "CORS_ORIGINS": "http://localhost:3000,https://server.epicrunze.com",
        "DEBUG": "true",
        "PASSWORD_RESET_EXPIRY": "15",  # 15 minutes
        "RATE_LIMIT_STORAGE_URL": redis_url,
        "API_BASE_URL": api_url,
        # Additional environment variables to match production
        "SIGNED_URL_EXPIRY": "3600",
        "ADMIN_PASSWORD": "test-admin-password",
        "TEXT_DATA_PATH": "/tmp/test_text",
        "WAV_DATA_PATH": "/tmp/test_wav",
        "SEGMENT_DATA_PATH": "/tmp/test_ogg",
        "META_DATA_PATH": "/tmp/test_meta",
        "CHUNK_SIZE_CHARS": "800",
        "SEGMENT_DURATION": "3.14",
        "OPUS_BITRATE": "32k",
        "LOG_LEVEL": "INFO",
        "ENVIRONMENT": "test"
    })

def cleanup_test_environment():
    """Clean up test files and databases."""
    test_db = "/tmp/test_audiobooks.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Clean up any test files
    test_dirs = ["/tmp/test_text", "/tmp/test_audio"]
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

def run_unit_tests():
    """Run unit tests."""
    print("🧪 Running unit tests...")
    
    # Add the services/api directory to Python path
    api_path = Path(__file__).parent.parent / "services" / "api"
    sys.path.insert(0, str(api_path))
    
    # Run pytest for API service test files
    api_test_files = [
        "tests/test_api.py",
        "tests/test_api_auth.py", 
        "tests/test_phase2_endpoints.py",
        "services/api/test_security.py",
        "services/api/test_auth_models.py",
        # Edge case tests (Priority 1 - Critical)
        "tests/test_error_boundaries.py",
        "tests/test_token_security.py", 
        "tests/test_rate_limiting_boundaries.py"
    ]
    
    result = subprocess.run([
        sys.executable, "-m", "pytest"] + api_test_files + [
        "-v", "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    # Now run storage service tests separately
    print("\n🧪 Running storage service tests...")
    
    # Add the services/storage directory to Python path
    storage_path = Path(__file__).parent.parent / "services" / "storage"
    sys.path.insert(0, str(storage_path))
    
    storage_result = subprocess.run([
        sys.executable, "-m", "pytest", "services/storage/test_auth_service.py",
        "-v", "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    # Return combined result
    return result.returncode == 0 and storage_result.returncode == 0

def run_integration_tests():
    """Run integration tests with actual API."""
    print("🔗 Running integration tests...")
    
    # Check if API is running
    try:
        import requests
        api_url = os.environ.get("API_BASE_URL")
        if not api_url:
            print("❌ API_BASE_URL environment variable not set")
            return False
        response = requests.get(f"{api_url}/health", timeout=5, verify=False)
        if response.status_code != 200:
            print("❌ API is not running. Start the API first with: docker-compose up -d api")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Start the API first with: docker-compose up -d api")
        return False
    
    # Run integration tests
    integration_tests = [
        "tests/test_api.py::TestIntegration",
        "tests/test_api_auth.py::TestCompleteAuthWorkflow",
        "tests/test_api_auth.py::TestBookOwnership",
        "tests/test_api_auth.py::TestBackwardsCompatibility"
    ]
    
    result = subprocess.run([
        sys.executable, "-m", "pytest"] + integration_tests + [
        "-v", 
        "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode == 0

def run_api_documentation_tests():
    """Test API documentation endpoints."""
    print("📚 Testing API documentation...")
    
    try:
        import requests
        api_url = os.environ.get("API_BASE_URL")
        if not api_url:
            print("❌ API_BASE_URL environment variable not set")
            return False
        
        # Test OpenAPI docs
        response = requests.get(f"{api_url}/docs", verify=False)
        if response.status_code == 200:
            print("✅ OpenAPI documentation accessible")
        else:
            print("❌ OpenAPI documentation not accessible")
            return False
        
        # Test health endpoint
        response = requests.get(f"{api_url}/health", verify=False)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check: {health_data['status']}")
            print(f"   Redis: {health_data['redis']}")
            print(f"   Database: {health_data['database']}")
        else:
            print("❌ Health check failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API documentation test failed: {e}")
        return False

def run_curl_tests():
    """Run curl-based API tests."""
    print("🌐 Running curl-based API tests...")
    
    api_url = os.environ.get("API_BASE_URL")
    if not api_url:
        print("❌ API_BASE_URL environment variable not set")
        return False
    
    test_script = f"""
#!/bin/bash

# Set API URL
API_URL="{api_url}"

# Test health endpoint
echo "Testing health endpoint..."
curl -s -k $API_URL/health | jq .

# Test authentication
echo -e "\nTesting authentication..."
curl -s -k -H "Authorization: Bearer invalid-key" $API_URL/api/v1/books
echo -e "\n"

# Test with valid auth
echo "Testing with valid authentication..."
curl -s -k -H "Authorization: Bearer default-dev-key" $API_URL/api/v1/books | jq .

# Create test file
echo "Creating test file..."
echo "This is a test audiobook content for curl testing." > /tmp/test_book.txt

# Test book submission
echo -e "\nTesting book submission..."
RESPONSE=$(curl -s -X POST $API_URL/api/v1/books \\
  -H "Authorization: Bearer default-dev-key" \\
  -F "title=Curl Test Book" \\
  -F "format=txt" \\
  -F "file=@/tmp/test_book.txt" \\
  -k)

echo $RESPONSE | jq .

# Extract book ID
BOOK_ID=$(echo $RESPONSE | jq -r '.book_id')
echo "Book ID: $BOOK_ID"

# Test status check
echo -e "\nTesting status check..."
curl -s -H "Authorization: Bearer default-dev-key" \\
  $API_URL/api/v1/books/$BOOK_ID/status | jq .

# Test chunks listing
echo -e "\nTesting chunks listing..."
curl -s -H "Authorization: Bearer default-dev-key" \\
  $API_URL/api/v1/books/$BOOK_ID/chunks | jq .

# Cleanup
rm -f /tmp/test_book.txt
"""
    
    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(test_script)
        script_path = f.name
    
    try:
        # Make script executable and run it
        os.chmod(script_path, 0o755)
        result = subprocess.run([script_path], shell=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
        
    finally:
        os.unlink(script_path)

def main():
    """Main test runner."""
    print("🚀 Audiobook Server API Test Suite")
    print("=" * 50)
    
    # Setup
    setup_test_environment()
    
    try:
        # Run different types of tests
        tests = [
            ("Unit Tests", run_unit_tests),
            ("API Documentation Tests", run_api_documentation_tests),
            ("Curl Tests", run_curl_tests),
            ("Integration Tests", run_integration_tests)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = test_func()
                results.append((test_name, success))
                if success:
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
                results.append((test_name, False))
        
        # Summary
        print(f"\n{'='*50}")
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nOverall: {passed}/{total} test suites passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return 0
        else:
            print("💥 Some tests failed!")
            return 1
            
    finally:
        cleanup_test_environment()

if __name__ == "__main__":
    sys.exit(main()) 