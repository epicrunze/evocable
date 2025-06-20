"""Test the text extraction functionality."""

import tempfile
import asyncio
from pathlib import Path
from main import extract_pdf_text, extract_epub_text, extract_txt_text, TextExtractor


def test_txt_extraction():
    """Test TXT file extraction with encoding detection."""
    # Create a test TXT file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Hello, World!\nThis is a test document.\n")
        temp_file = f.name
    
    try:
        result = extract_txt_text(temp_file)
        assert result.success
        assert "Hello, World!" in result.text
        assert "test document" in result.text
        print("✓ TXT extraction test passed")
    finally:
        Path(temp_file).unlink()


def test_pdf_extraction():
    """Test PDF extraction (requires a test PDF file)."""
    # This would require a test PDF file
    # For now, just test the function exists
    assert callable(extract_pdf_text)
    print("✓ PDF extraction function exists")


def test_epub_extraction():
    """Test EPUB extraction (requires a test EPUB file)."""
    # This would require a test EPUB file
    # For now, just test the function exists
    assert callable(extract_epub_text)
    print("✓ EPUB extraction function exists")


async def test_extractor_class():
    """Test the TextExtractor class initialization."""
    extractor = TextExtractor(
        storage_url="http://localhost:8001",
        redis_url="redis://localhost:6379"
    )
    
    assert extractor.storage_url == "http://localhost:8001"
    assert extractor.extractors['.txt'] == extract_txt_text
    assert extractor.extractors['.pdf'] == extract_pdf_text
    assert extractor.extractors['.epub'] == extract_epub_text
    print("✓ TextExtractor class test passed")


if __name__ == "__main__":
    print("Running ingest service tests...")
    
    test_txt_extraction()
    test_pdf_extraction()
    test_epub_extraction()
    asyncio.run(test_extractor_class())
    
    print("All tests passed!") 