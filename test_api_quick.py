#!/usr/bin/env python3
"""Quick API test script for the Audiobook Server."""

import requests
import tempfile
import json
import sys
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
API_KEY = "default-dev-key"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def test_health():
    """Test health endpoint."""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {data['status']}")
            print(f"   Redis: {data['redis']}")
            print(f"   Database: {data['database']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def test_authentication():
    """Test authentication."""
    print("\n🔐 Testing authentication...")
    
    # Test invalid key
    response = requests.get(f"{API_BASE}/api/v1/books", 
                          headers={"Authorization": "Bearer invalid-key"})
    if response.status_code == 401:
        print("✅ Invalid auth correctly rejected")
    else:
        print(f"❌ Invalid auth not rejected: {response.status_code}")
        return False
    
    # Test valid key
    response = requests.get(f"{API_BASE}/api/v1/books", headers=HEADERS)
    if response.status_code == 200:
        print("✅ Valid auth accepted")
        return True
    else:
        print(f"❌ Valid auth rejected: {response.status_code}")
        return False

def test_book_submission():
    """Test book submission."""
    print("\n📚 Testing book submission...")
    
    # Create test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test audiobook content for API testing.\n" * 10)
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            response = requests.post(
                f"{API_BASE}/api/v1/books",
                headers=HEADERS,
                data={"title": "API Test Book", "format": "txt"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Book submitted: {data['book_id']}")
            return data['book_id']
        else:
            print(f"❌ Book submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    finally:
        Path(temp_file).unlink()

def test_book_status(book_id):
    """Test book status endpoint."""
    print(f"\n📊 Testing book status for {book_id}...")
    
    response = requests.get(f"{API_BASE}/api/v1/books/{book_id}/status", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {data['status']} ({data['percent_complete']}%)")
        return True
    else:
        print(f"❌ Status check failed: {response.status_code}")
        return False

def test_chunks_listing(book_id):
    """Test chunks listing."""
    print(f"\n🎵 Testing chunks listing for {book_id}...")
    
    response = requests.get(f"{API_BASE}/api/v1/books/{book_id}/chunks", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chunks: {data['total_chunks']} chunks, {data['total_duration_s']}s total")
        return True
    else:
        print(f"❌ Chunks listing failed: {response.status_code}")
        return False

def test_error_handling():
    """Test error handling."""
    print("\n⚠️  Testing error handling...")
    
    # Test non-existent book
    response = requests.get(f"{API_BASE}/api/v1/books/non-existent-id/status", headers=HEADERS)
    if response.status_code == 404:
        print("✅ 404 correctly returned for non-existent book")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
        return False
    
    # Test invalid format
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content")
        temp_file = f.name
    
    try:
        with open(temp_file, 'rb') as f:
            response = requests.post(
                f"{API_BASE}/api/v1/books",
                headers=HEADERS,
                data={"title": "Test", "format": "invalid"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        if response.status_code == 400:
            print("✅ 400 correctly returned for invalid format")
            return True
        else:
            print(f"❌ Expected 400, got {response.status_code}")
            return False
    finally:
        Path(temp_file).unlink()

def main():
    """Run all tests."""
    print("🚀 Audiobook Server API Quick Test")
    print("=" * 40)
    
    tests = [
        ("Health Check", test_health),
        ("Authentication", test_authentication),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Test book submission and related endpoints
    book_id = test_book_submission()
    if book_id:
        results.append(("Book Submission", True))
        
        # Test status and chunks
        results.append(("Book Status", test_book_status(book_id)))
        results.append(("Chunks Listing", test_chunks_listing(book_id)))
    else:
        results.append(("Book Submission", False))
    
    # Summary
    print(f"\n{'='*40}")
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 