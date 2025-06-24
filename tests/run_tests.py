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
    os.environ.update({
        "API_KEY": "test-api-key",
        "DATABASE_PATH": "/tmp/test_audiobooks.db",
        "REDIS_URL": "redis://localhost:6379",
        "STORAGE_URL": "http://localhost:8001",
        "INGEST_URL": "http://localhost:8002",
        "CORS_ORIGINS": "http://localhost:3000",
        "DEBUG": "true"
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
    
    # Run pytest
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_api.py", 
        "-v", 
        "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode == 0

def run_integration_tests():
    """Run integration tests with actual API."""
    print("🔗 Running integration tests...")
    
    # Check if API is running
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API is not running. Start the API first with: docker-compose up -d api")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Start the API first with: docker-compose up -d api")
        return False
    
    # Run integration tests
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_api.py::TestIntegration", 
        "-v", 
        "--tb=short"
    ], cwd=Path(__file__).parent.parent)
    
    return result.returncode == 0

def run_api_documentation_tests():
    """Test API documentation endpoints."""
    print("📚 Testing API documentation...")
    
    try:
        import requests
        
        # Test OpenAPI docs
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ OpenAPI documentation accessible")
        else:
            print("❌ OpenAPI documentation not accessible")
            return False
        
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
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
    
    test_script = """
#!/bin/bash

# Test health endpoint
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | jq .

# Test authentication
echo -e "\nTesting authentication..."
curl -s -H "Authorization: Bearer invalid-key" http://localhost:8000/api/v1/books
echo -e "\n"

# Test with valid auth
echo "Testing with valid authentication..."
curl -s -H "Authorization: Bearer default-dev-key" http://localhost:8000/api/v1/books | jq .

# Create test file
echo "Creating test file..."
echo "This is a test audiobook content for curl testing." > /tmp/test_book.txt

# Test book submission
echo -e "\nTesting book submission..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/books \\
  -H "Authorization: Bearer default-dev-key" \\
  -F "title=Curl Test Book" \\
  -F "format=txt" \\
  -F "file=@/tmp/test_book.txt")

echo $RESPONSE | jq .

# Extract book ID
BOOK_ID=$(echo $RESPONSE | jq -r '.book_id')
echo "Book ID: $BOOK_ID"

# Test status check
echo -e "\nTesting status check..."
curl -s -H "Authorization: Bearer default-dev-key" \\
  http://localhost:8000/api/v1/books/$BOOK_ID/status | jq .

# Test chunks listing
echo -e "\nTesting chunks listing..."
curl -s -H "Authorization: Bearer default-dev-key" \\
  http://localhost:8000/api/v1/books/$BOOK_ID/chunks | jq .

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