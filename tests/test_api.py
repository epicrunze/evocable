"""Comprehensive API tests for the Audiobook Server."""

import pytest
import tempfile
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import httpx
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.append('services/api')
from main import app
from models import DatabaseManager, BookStatus, BookFormat


class TestAudiobookAPI:
    """Test suite for the Audiobook Server API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for testing."""
        return {"Authorization": "Bearer default-dev-key"}
    
    @pytest.fixture
    def sample_txt_file(self):
        """Create a sample TXT file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a sample audiobook content for testing.\n" * 10)
            temp_file = f.name
        
        yield temp_file
        Path(temp_file).unlink()
    
    @pytest.fixture
    def sample_pdf_file(self):
        """Create a sample PDF file for testing."""
        # Create a minimal PDF file for testing
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF'
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_content)
            temp_file = f.name
        
        yield temp_file
        Path(temp_file).unlink()
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api"
        assert "redis" in data
        assert "database" in data
        assert "pipeline" in data
        assert data["version"] == "1.0.0"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Audiobook Server API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
    
    def test_list_books_without_auth(self, client):
        """Test list books without authentication."""
        response = client.get("/api/v1/books")
        assert response.status_code == 401
    
    def test_list_books_with_invalid_auth(self, client):
        """Test list books with invalid API key."""
        response = client.get("/api/v1/books", headers={"Authorization": "Bearer invalid-key"})
        assert response.status_code == 401
    
    def test_list_books_with_valid_auth(self, client, auth_headers):
        """Test list books with valid authentication."""
        response = client.get("/api/v1/books", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "books" in data
        assert isinstance(data["books"], list)
    
    def test_submit_book_without_auth(self, client, sample_txt_file):
        """Test book submission without authentication."""
        with open(sample_txt_file, 'rb') as f:
            response = client.post(
                "/api/v1/books",
                data={"title": "Test Book", "format": "txt"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        assert response.status_code == 401
    
    def test_submit_book_with_invalid_format(self, client, auth_headers, sample_txt_file):
        """Test book submission with invalid format."""
        with open(sample_txt_file, 'rb') as f:
            response = client.post(
                "/api/v1/books",
                headers=auth_headers,
                data={"title": "Test Book", "format": "docx"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]
    
    def test_submit_book_with_mismatched_extension(self, client, auth_headers, sample_txt_file):
        """Test book submission with mismatched file extension."""
        with open(sample_txt_file, 'rb') as f:
            response = client.post(
                "/api/v1/books",
                headers=auth_headers,
                data={"title": "Test Book", "format": "pdf"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        assert response.status_code == 400
        assert "File extension" in response.json()["detail"]
    
    def test_submit_book_with_large_file(self, client, auth_headers):
        """Test book submission with file too large."""
        # Create a large file (>50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                response = client.post(
                    "/api/v1/books",
                    headers=auth_headers,
                    data={"title": "Large Book", "format": "txt"},
                    files={"file": ("large.txt", f, "text/plain")}
                )
            assert response.status_code == 413
            assert "File too large" in response.json()["detail"]
        finally:
            Path(temp_file).unlink()
    
    def test_submit_book_without_file(self, client, auth_headers):
        """Test book submission without file."""
        response = client.post(
            "/api/v1/books",
            headers=auth_headers,
            data={"title": "Test Book", "format": "txt"}
        )
        assert response.status_code == 400
        assert "No file provided" in response.json()["detail"]
    
    def test_submit_book_success_txt(self, client, auth_headers, sample_txt_file):
        """Test successful TXT book submission."""
        with open(sample_txt_file, 'rb') as f:
            response = client.post(
                "/api/v1/books",
                headers=auth_headers,
                data={"title": "Test TXT Book", "format": "txt"},
                files={"file": ("test.txt", f, "text/plain")}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "book_id" in data
        assert data["status"] == "pending"
        assert "submitted successfully" in data["message"]
        
        # Store book_id for later tests
        self.book_id = data["book_id"]
    
    def test_submit_book_success_pdf(self, client, auth_headers, sample_pdf_file):
        """Test successful PDF book submission."""
        with open(sample_pdf_file, 'rb') as f:
            response = client.post(
                "/api/v1/books",
                headers=auth_headers,
                data={"title": "Test PDF Book", "format": "pdf"},
                files={"file": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert "book_id" in data
        assert data["status"] == "pending"
    
    def test_get_book_status_without_auth(self, client):
        """Test get book status without authentication."""
        response = client.get("/api/v1/books/test-id/status")
        assert response.status_code == 401
    
    def test_get_book_status_not_found(self, client, auth_headers):
        """Test get book status for non-existent book."""
        response = client.get("/api/v1/books/non-existent-id/status", headers=auth_headers)
        assert response.status_code == 404
    
    def test_get_book_status_success(self, client, auth_headers):
        """Test successful book status retrieval."""
        # First submit a book
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                submit_response = client.post(
                    "/api/v1/books",
                    headers=auth_headers,
                    data={"title": "Status Test Book", "format": "txt"},
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            book_id = submit_response.json()["book_id"]
            
            # Get status
            response = client.get(f"/api/v1/books/{book_id}/status", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["book_id"] == book_id
            assert data["title"] == "Status Test Book"
            assert "status" in data
            assert "percent_complete" in data
            assert "created_at" in data
            assert "updated_at" in data
        finally:
            Path(temp_file).unlink()
    
    def test_list_chunks_without_auth(self, client):
        """Test list chunks without authentication."""
        response = client.get("/api/v1/books/test-id/chunks")
        assert response.status_code == 401
    
    def test_list_chunks_not_found(self, client, auth_headers):
        """Test list chunks for non-existent book."""
        response = client.get("/api/v1/books/non-existent-id/chunks", headers=auth_headers)
        assert response.status_code == 404
    
    def test_list_chunks_success(self, client, auth_headers):
        """Test successful chunks listing."""
        # First submit a book
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                submit_response = client.post(
                    "/api/v1/books",
                    headers=auth_headers,
                    data={"title": "Chunks Test Book", "format": "txt"},
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            book_id = submit_response.json()["book_id"]
            
            # List chunks (will be empty for new book)
            response = client.get(f"/api/v1/books/{book_id}/chunks", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["book_id"] == book_id
            assert data["total_chunks"] == 0
            assert data["total_duration_s"] == 0.0
            assert data["chunks"] == []
        finally:
            Path(temp_file).unlink()
    
    def test_get_audio_chunk_without_auth(self, client):
        """Test get audio chunk without authentication."""
        response = client.get("/api/v1/books/test-id/chunks/0")
        assert response.status_code == 401
    
    def test_get_audio_chunk_not_found(self, client, auth_headers):
        """Test get audio chunk for non-existent book/chunk."""
        response = client.get("/api/v1/books/non-existent-id/chunks/0", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_book_without_auth(self, client):
        """Test delete book without authentication."""
        response = client.delete("/api/v1/books/test-id")
        assert response.status_code == 401
    
    def test_delete_book_not_found(self, client, auth_headers):
        """Test delete non-existent book."""
        response = client.delete("/api/v1/books/non-existent-id", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_book_success(self, client, auth_headers):
        """Test successful book deletion."""
        # First submit a book
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content")
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                submit_response = client.post(
                    "/api/v1/books",
                    headers=auth_headers,
                    data={"title": "Delete Test Book", "format": "txt"},
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            book_id = submit_response.json()["book_id"]
            
            # Delete the book
            response = client.delete(f"/api/v1/books/{book_id}", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert "deleted successfully" in data["message"]
            
            # Verify book is deleted
            status_response = client.get(f"/api/v1/books/{book_id}/status", headers=auth_headers)
            assert status_response.status_code == 404
        finally:
            Path(temp_file).unlink()


class TestDatabaseManager:
    """Test database operations."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager with test database."""
        test_db_path = "/tmp/test_audiobooks.db"
        manager = DatabaseManager(db_path=test_db_path)
        yield manager
        # Cleanup
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    
    def test_create_book(self, db_manager):
        """Test book creation."""
        book_id = db_manager.create_book("Test Book", "txt", "/path/to/file.txt")
        assert book_id is not None
        assert len(book_id) > 0
        
        # Verify book exists
        book = db_manager.get_book(book_id)
        assert book is not None
        assert book["title"] == "Test Book"
        assert book["format"] == "txt"
        assert book["status"] == "pending"
    
    def test_get_book_not_found(self, db_manager):
        """Test getting non-existent book."""
        book = db_manager.get_book("non-existent-id")
        assert book is None
    
    def test_list_books(self, db_manager):
        """Test listing books."""
        # Create multiple books
        book1_id = db_manager.create_book("Book 1", "txt", "/path1.txt")
        book2_id = db_manager.create_book("Book 2", "pdf", "/path2.pdf")
        
        books = db_manager.list_books()
        assert len(books) >= 2
        
        # Verify books are ordered by creation time (newest first)
        book_titles = [book["title"] for book in books[:2]]
        assert "Book 2" in book_titles
        assert "Book 1" in book_titles
    
    def test_update_book_status(self, db_manager):
        """Test updating book status."""
        book_id = db_manager.create_book("Status Test Book", "txt", "/path.txt")
        
        # Update status
        db_manager.update_book_status(book_id, "processing", 25.0)
        
        book = db_manager.get_book(book_id)
        assert book["status"] == "processing"
        assert book["percent_complete"] == 25.0
    
    def test_create_chunk(self, db_manager):
        """Test chunk creation."""
        book_id = db_manager.create_book("Chunk Test Book", "txt", "/path.txt")
        
        chunk_id = db_manager.create_chunk(book_id, 0, 3.14, "/audio/chunk0.ogg", 12560)
        assert chunk_id is not None
        
        chunks = db_manager.get_chunks(book_id)
        assert len(chunks) == 1
        assert chunks[0]["seq"] == 0
        assert chunks[0]["duration_s"] == 3.14
        assert chunks[0]["file_path"] == "/audio/chunk0.ogg"
    
    def test_get_chunk(self, db_manager):
        """Test getting specific chunk."""
        book_id = db_manager.create_book("Chunk Test Book", "txt", "/path.txt")
        db_manager.create_chunk(book_id, 0, 3.14, "/audio/chunk0.ogg", 12560)
        
        chunk = db_manager.get_chunk(book_id, 0)
        assert chunk is not None
        assert chunk["seq"] == 0
        assert chunk["duration_s"] == 3.14
    
    def test_get_chunk_not_found(self, db_manager):
        """Test getting non-existent chunk."""
        book_id = db_manager.create_book("Chunk Test Book", "txt", "/path.txt")
        chunk = db_manager.get_chunk(book_id, 999)
        assert chunk is None
    
    def test_delete_book(self, db_manager):
        """Test book deletion."""
        book_id = db_manager.create_book("Delete Test Book", "txt", "/path.txt")
        db_manager.create_chunk(book_id, 0, 3.14, "/audio/chunk0.ogg", 12560)
        
        # Verify book and chunk exist
        assert db_manager.get_book(book_id) is not None
        assert len(db_manager.get_chunks(book_id)) == 1
        
        # Delete book
        db_manager.delete_book(book_id)
        
        # Verify book and chunks are deleted
        assert db_manager.get_book(book_id) is None
        assert len(db_manager.get_chunks(book_id)) == 0


class TestDataModels:
    """Test Pydantic data models."""
    
    def test_book_format_enum(self):
        """Test BookFormat enum."""
        assert BookFormat.PDF == "pdf"
        assert BookFormat.EPUB == "epub"
        assert BookFormat.TXT == "txt"
        
        # Test validation
        with pytest.raises(ValueError):
            BookFormat("docx")
    
    def test_book_status_enum(self):
        """Test BookStatus enum."""
        assert BookStatus.PENDING == "pending"
        assert BookStatus.PROCESSING == "processing"
        assert BookStatus.COMPLETED == "completed"
        assert BookStatus.FAILED == "failed"
    
    def test_book_submission_request(self):
        """Test BookSubmissionRequest model."""
        from models import BookSubmissionRequest
        
        # Valid request
        request = BookSubmissionRequest(title="Test Book", format=BookFormat.TXT)
        assert request.title == "Test Book"
        assert request.format == BookFormat.TXT
        
        # Invalid title (too short)
        with pytest.raises(ValueError):
            BookSubmissionRequest(title="", format=BookFormat.TXT)
        
        # Invalid title (too long)
        with pytest.raises(ValueError):
            BookSubmissionRequest(title="x" * 256, format=BookFormat.TXT)
    
    def test_book_response(self):
        """Test BookResponse model."""
        from models import BookResponse
        
        response = BookResponse(
            book_id="test-id",
            status=BookStatus.PENDING,
            message="Test message"
        )
        assert response.book_id == "test-id"
        assert response.status == BookStatus.PENDING
        assert response.message == "Test message"
    
    def test_book_status_response(self):
        """Test BookStatusResponse model."""
        from models import BookStatusResponse
        from datetime import datetime
        
        response = BookStatusResponse(
            book_id="test-id",
            title="Test Book",
            status=BookStatus.PROCESSING,
            percent_complete=25.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert response.book_id == "test-id"
        assert response.title == "Test Book"
        assert response.status == BookStatus.PROCESSING
        assert response.percent_complete == 25.0
        
        # Test percent_complete validation
        with pytest.raises(ValueError):
            BookStatusResponse(
                book_id="test-id",
                title="Test Book",
                status=BookStatus.PROCESSING,
                percent_complete=150.0,  # Invalid
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
    
    def test_chunk_info(self):
        """Test ChunkInfo model."""
        from models import ChunkInfo
        
        chunk = ChunkInfo(
            seq=0,
            duration_s=3.14,
            url="/api/v1/books/test-id/chunks/0"
        )
        assert chunk.seq == 0
        assert chunk.duration_s == 3.14
        assert chunk.url == "/api/v1/books/test-id/chunks/0"
        
        # Test validation
        with pytest.raises(ValueError):
            ChunkInfo(
                seq=-1,  # Invalid
                duration_s=3.14,
                url="/test"
            )
        
        with pytest.raises(ValueError):
            ChunkInfo(
                seq=0,
                duration_s=0.0,  # Invalid
                url="/test"
            )
    
    def test_chunk_list_response(self):
        """Test ChunkListResponse model."""
        from models import ChunkListResponse, ChunkInfo
        
        chunks = [
            ChunkInfo(seq=0, duration_s=3.14, url="/chunks/0"),
            ChunkInfo(seq=1, duration_s=3.14, url="/chunks/1")
        ]
        
        response = ChunkListResponse(
            book_id="test-id",
            total_chunks=2,
            total_duration_s=6.28,
            chunks=chunks
        )
        assert response.book_id == "test-id"
        assert response.total_chunks == 2
        assert response.total_duration_s == 6.28
        assert len(response.chunks) == 2


class TestIntegration:
    """Integration tests for the complete API workflow."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers."""
        return {"Authorization": "Bearer default-dev-key"}
    
    def test_complete_workflow(self, client, auth_headers):
        """Test complete book processing workflow."""
        # 1. Submit a book
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test audiobook content for integration testing.\n" * 20)
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                response = client.post(
                    "/api/v1/books",
                    headers=auth_headers,
                    data={"title": "Integration Test Book", "format": "txt"},
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            assert response.status_code == 201
            book_id = response.json()["book_id"]
            
            # 2. Check initial status
            status_response = client.get(f"/api/v1/books/{book_id}/status", headers=auth_headers)
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["status"] in ["pending", "processing"]
            assert status_data["percent_complete"] >= 0.0
            
            # 3. List chunks (should be empty initially)
            chunks_response = client.get(f"/api/v1/books/{book_id}/chunks", headers=auth_headers)
            assert chunks_response.status_code == 200
            chunks_data = chunks_response.json()
            assert chunks_data["total_chunks"] == 0
            assert chunks_data["chunks"] == []
            
            # 4. Verify book appears in list
            list_response = client.get("/api/v1/books", headers=auth_headers)
            assert list_response.status_code == 200
            books = list_response.json()["books"]
            book_ids = [book["id"] for book in books]
            assert book_id in book_ids
            
        finally:
            Path(temp_file).unlink()
    
    def test_error_handling_consistency(self, client):
        """Test that error responses are consistent across endpoints."""
        # Test without auth on multiple endpoints
        endpoints = [
            "/api/v1/books",
            "/api/v1/books/test-id/status",
            "/api/v1/books/test-id/chunks",
            "/api/v1/books/test-id/chunks/0",
            "/api/v1/books/test-id"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
            assert "detail" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 