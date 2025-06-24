# Audiobook Server API Documentation

## Overview

The Audiobook Server API converts PDF, EPUB, and TXT files into streaming audiobooks. The system processes documents through a pipeline: text extraction → segmentation → TTS generation → audio transcoding.

**Base URL**: `http://localhost:8000`  
**Authentication**: Bearer token (API key)  
**Content-Type**: `application/json` (except file uploads)

## Authentication

All endpoints require authentication via Bearer token in the Authorization header:

```bash
Authorization: Bearer your-api-key-here
```

**Default Development Key**: `default-dev-key`

## Endpoints

### Health Check

#### `GET /health`

Check service health and dependencies.

**Response**:
```json
{
  "status": "healthy",
  "service": "api",
  "redis": "healthy",
  "database": "healthy",
  "pipeline": {
    "redis": "healthy",
    "database": "healthy",
    "pipeline": "ready"
  },
  "version": "1.0.0"
}
```

**Status Codes**:
- `200`: Service healthy
- `503`: Service unhealthy (check individual component status)

---

### Book Management

#### `GET /api/v1/books`

List all books (also validates API key).

**Headers**:
```
Authorization: Bearer your-api-key
```

**Response**:
```json
{
  "books": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Sample Book",
      "format": "pdf",
      "status": "completed",
      "percent_complete": 100.0,
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:35:00",
      "total_chunks": 15
    }
  ]
}
```

**Status Codes**:
- `200`: Success
- `401`: Invalid API key

---

#### `POST /api/v1/books`

Submit a book for processing.

**Headers**:
```
Authorization: Bearer your-api-key
Content-Type: multipart/form-data
```

**Form Data**:
- `title` (string, required): Book title (1-255 characters)
- `format` (string, required): File format (`pdf`, `epub`, `txt`)
- `file` (file, required): Book file (max 50MB)

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=My Sample Book" \
  -F "format=pdf" \
  -F "file=@sample.pdf"
```

**Response**:
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Book 'My Sample Book' submitted successfully for processing"
}
```

**Status Codes**:
- `201`: Book submitted successfully
- `400`: Invalid format, file type, or file size
- `401`: Invalid API key
- `413`: File too large (>50MB)

**Validation Rules**:
- File extension must match format (`.pdf` for PDF, `.epub` for EPUB, `.txt` for TXT)
- Maximum file size: 50MB
- Title length: 1-255 characters

---

#### `GET /api/v1/books/{book_id}/status`

Get processing status and progress for a book.

**Headers**:
```
Authorization: Bearer your-api-key
```

**Response**:
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Sample Book",
  "status": "processing",
  "percent_complete": 25.0,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:32:00",
  "total_chunks": null
}
```

**Status Codes**:
- `200`: Success
- `401`: Invalid API key
- `404`: Book not found

**Processing Status Values**:
- `pending`: Book submitted, awaiting processing
- `processing`: Background pipeline initiated (5%)
- `extracting`: Text extraction in progress (10%)
- `segmenting`: Text chunking in progress (25%)
- `generating_audio`: TTS processing (50%)
- `transcoding`: Audio format conversion (75%)
- `completed`: Ready for streaming (100%)
- `failed`: Error occurred (check `error_message`)

---

### Audio Streaming

#### `GET /api/v1/books/{book_id}/chunks`

List available audio chunks for a book.

**Headers**:
```
Authorization: Bearer your-api-key
```

**Response**:
```json
{
  "book_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_chunks": 15,
  "total_duration_s": 47.1,
  "chunks": [
    {
      "seq": 0,
      "duration_s": 3.14,
      "url": "/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/0",
      "file_size": 12560
    },
    {
      "seq": 1,
      "duration_s": 3.14,
      "url": "/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/1",
      "file_size": 12840
    }
  ]
}
```

**Status Codes**:
- `200`: Success
- `401`: Invalid API key
- `404`: Book not found

---

#### `GET /api/v1/books/{book_id}/chunks/{seq}`

Stream an audio chunk file.

**Headers**:
```
Authorization: Bearer your-api-key
```

**Response**: Audio file (Opus format, Ogg container)

**Headers in Response**:
```
Content-Type: audio/ogg
Content-Length: 12560
Accept-Ranges: bytes
```

**Status Codes**:
- `200`: Audio chunk returned
- `401`: Invalid API key
- `404`: Book or chunk not found

**Example**:
```bash
curl -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/550e8400-e29b-41d4-a716-446655440000/chunks/0 \
  -o chunk_0.ogg
```

---

### Book Management

#### `DELETE /api/v1/books/{book_id}`

Delete a book and all associated audio chunks.

**Headers**:
```
Authorization: Bearer your-api-key
```

**Response**:
```json
{
  "message": "Book deleted successfully"
}
```

**Status Codes**:
- `200`: Book deleted successfully
- `401`: Invalid API key
- `404`: Book not found

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "validation_error",
  "message": "Invalid file format. Supported formats: pdf, epub, txt",
  "details": {
    "field": "format",
    "value": "docx"
  }
}
```

**Common Error Types**:
- `validation_error`: Invalid input data
- `authentication_error`: Invalid API key
- `not_found`: Resource not found
- `file_too_large`: File exceeds size limit
- `processing_error`: Pipeline processing failed

## Processing Pipeline

The system processes books through these stages:

1. **Upload** → `pending` (0%)
2. **Text Extraction** → `extracting` (10%)
3. **Segmentation** → `segmenting` (25%)
4. **TTS Generation** → `generating_audio` (50%)
5. **Transcoding** → `transcoding` (75%)
6. **Complete** → `completed` (100%)

**Typical Processing Times**:
- Small book (<10 pages): 2-5 minutes
- Medium book (10-50 pages): 5-15 minutes
- Large book (>50 pages): 15+ minutes

## Audio Format

- **Codec**: Opus
- **Container**: Ogg
- **Bitrate**: 32 kbps
- **Chunk Duration**: 3.14 seconds
- **Sample Rate**: 22050 Hz

## Rate Limits

- File uploads: 10 per minute per API key
- Status checks: 60 per minute per API key
- Audio streaming: No limits

## Examples

### Complete Workflow

```bash
# 1. Submit a book
BOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=Sample Book" \
  -F "format=txt" \
  -F "file=@sample.txt")

BOOK_ID=$(echo $BOOK_RESPONSE | jq -r '.book_id')
echo "Book ID: $BOOK_ID"

# 2. Monitor processing
while true; do
  STATUS=$(curl -s -H "Authorization: Bearer default-dev-key" \
    http://localhost:8000/api/v1/books/$BOOK_ID/status)
  
  echo "Status: $(echo $STATUS | jq -r '.status') - $(echo $STATUS | jq -r '.percent_complete')%"
  
  if [ "$(echo $STATUS | jq -r '.status')" = "completed" ]; then
    break
  fi
  
  sleep 10
done

# 3. List chunks
curl -s -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/$BOOK_ID/chunks | jq .

# 4. Stream first chunk
curl -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/$BOOK_ID/chunks/0 \
  -o first_chunk.ogg
```

### Error Handling

```bash
# Invalid API key
curl -H "Authorization: Bearer invalid-key" \
  http://localhost:8000/api/v1/books
# Returns 401 Unauthorized

# File too large
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=Large Book" \
  -F "format=txt" \
  -F "file=@large_file.txt"
# Returns 413 Request Entity Too Large

# Invalid format
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=Invalid Book" \
  -F "format=docx" \
  -F "file=@document.docx"
# Returns 400 Bad Request
``` 