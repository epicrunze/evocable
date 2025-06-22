#!/usr/bin/env python3
"""Script to register existing audio chunks with the storage service."""

import json
import requests

def register_book_chunks(book_id: str):
    """Register audio chunks for a book with the storage service."""
    try:
        # Read the metadata file
        metadata_file = f"/tmp/{book_id}_metadata.json"
        
        # First, copy the metadata from the container
        import subprocess
        subprocess.run([
            "docker-compose", "exec", "-T", "storage", 
            "cat", f"/data/ogg/{book_id}/metadata.json"
        ], stdout=open(metadata_file, 'w'), check=True)
        
        # Read the metadata
        with open(metadata_file, 'r') as f:
            chunks = json.load(f)
        
        # Prepare the API payload
        chunk_data = {
            "chunks": chunks
        }
        
        # Call the storage service API
        response = requests.post(
            f"http://localhost:8001/books/{book_id}/audio-chunks",
            json=chunk_data
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully registered {len(chunks)} chunks for book {book_id}")
        else:
            print(f"❌ Failed to register chunks: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error registering chunks for book {book_id}: {e}")

if __name__ == "__main__":
    # Register chunks for both completed books
    books = [
        "9ce48cb7-e7a5-4adf-b613-0468c2a7393d",
        "42c39529-3fe8-4c04-8e33-b991c8015ad8"
    ]
    
    for book_id in books:
        register_book_chunks(book_id) 