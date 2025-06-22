# Audiobook Server

Convert user-provided PDF, EPUB, or TXT files into streamed English audiobook audio via a React PWA.

## 🎯 Project Overview

This system transforms text documents into high-quality audio streams using:
- **Text Extraction**: PDF (pdfplumber), EPUB (ebooklib), TXT with OCR fallback (Tesseract)
- **Text Processing**: spaCy sentence tokenization with 800-character chunking and SSML markup
- **Text-to-Speech**: FastPitch 2 + HiFiGAN on NVIDIA RTX 3090 for production-grade audio
- **Audio Streaming**: FFmpeg transcoding to Opus@32kbps in Ogg containers, segmented for streaming
- **Modern PWA**: React client with offline caching and real-time status updates

## 🚧 Current Implementation Status

### ✅ Phase 1: Data Models & API Foundation (COMPLETED)
- **Pydantic Models**: Complete request/response schemas for all API endpoints
- **Database Models**: SQLite schema with books and chunks tables
- **API Foundation**: FastAPI app with authentication, health checks, and placeholder endpoints
- **Docker Integration**: Containerized services with proper permissions and data volumes
- **Testing**: Comprehensive validation of data models and database operations

### ✅ Phase 2: Core API Endpoints (COMPLETED)
- **Book Submission**: Full file upload with validation, storage, and database integration
- **Status Checking**: Real-time book processing status with progress tracking
- **Chunk Listing**: Audio chunk metadata with duration and URL generation
- **Audio Streaming**: File serving with proper content types and error handling
- **Authentication**: API key protection on all endpoints
- **Validation**: File format, size, and extension validation
- **Error Handling**: Comprehensive HTTP status codes and error messages

### ✅ Phase 3: Service Integration (COMPLETED)
- **Background Task Management**: Async pipeline monitoring with FastAPI lifespan
- **Processing Pipeline**: Complete orchestration from upload to text extraction
- **Redis Queue System**: Reliable task queuing and inter-service communication
- **Real-time Status Updates**: Live progress tracking with percentage completion
- **Service Communication**: HTTP + Redis messaging between API, ingest, and storage
- **Shared Volume Management**: Proper Docker volume configuration for file sharing
- **Error Propagation**: Comprehensive error handling throughout the pipeline

### 🔄 Phase 4: Complete Processing Pipeline (NEXT)
- Segmenter service integration for text chunking and SSML generation
- TTS worker service with FastPitch + HiFiGAN integration
- Transcoder service for audio format conversion and streaming
- End-to-end audiobook generation workflow

### ⏳ Phase 5: Error Handling & Validation (PLANNED)
- Enhanced logging and monitoring integration
- Performance optimization and caching
- Rate limiting and security enhancements

### ⏳ Phase 6: Testing & Documentation (PLANNED)
- Unit and integration tests
- End-to-end pipeline testing
- Performance benchmarking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React PWA     │    │   FastAPI       │    │   Redis Queue   │
│   (Port 3000)   │◄──►│   (Port 8000)   │◄──►│   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Storage       │
                       │   (Port 8001)   │
                       │   SQLite + FS   │
                       └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingest        │    │   Segmenter     │    │   TTS Worker    │
│   (Text Extract)│───►│   (Chunk + SSML)│───►│   (FastPitch)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Transcoder    │
                                              │   (FFmpeg)      │
                                              │   WAV → Opus    │
                                              └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with CUDA support (RTX 3090 recommended)
- NVIDIA Container Toolkit installed

### Setup

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd evocable
   cp env.example .env
   # Edit .env with your API_KEY and other settings
   ```

2. **Start the system**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - API Health Check: http://localhost:8000/health
   - API Documentation: http://localhost:8000/docs
   - Storage Service: http://localhost:8001/health
   - PWA Client: http://localhost:3000 (coming soon)

### Current API Testing

```bash
# Test API health (includes database and pipeline status)
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"api","redis":"healthy","database":"healthy","pipeline":{"redis":"healthy","database":"healthy","pipeline":"ready"},"version":"1.0.0"}

# Test complete processing pipeline
echo "This is a test audiobook content." > sample.txt

# Submit book and watch processing
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=Test Book Pipeline" \
  -F "format=txt" \
  -F "file=@sample.txt"

# Check status immediately (should show PROCESSING or EXTRACTING)
curl -H "Authorization: Bearer default-dev-key" \
     http://localhost:8000/api/v1/books/BOOK_ID/status

# Wait a few seconds and check again (should show SEGMENTING at 25%)
sleep 5
curl -H "Authorization: Bearer default-dev-key" \
     http://localhost:8000/api/v1/books/BOOK_ID/status

# Test chunk listing (empty until full pipeline is complete)
curl -H "Authorization: Bearer default-dev-key" \
     http://localhost:8000/api/v1/books/BOOK_ID/chunks
```

## 📁 Project Structure

```
evocable/
├── services/
│   ├── api/                  # FastAPI gateway and orchestration
│   │   ├── main.py          # ✅ FastAPI app with auth & health checks
│   │   ├── models.py        # ✅ Pydantic models & database manager
│   │   ├── background_tasks.py # ✅ Pipeline orchestration & monitoring
│   │   ├── Dockerfile       # ✅ Container with proper permissions
│   │   └── requirements.txt # ✅ Dependencies
│   ├── storage/             # Centralized metadata and file management
│   ├── ingest/              # Text extraction from PDF/EPUB/TXT
│   ├── segmenter/           # Text chunking and SSML generation
│   ├── tts-worker/          # FastPitch + HiFiGAN TTS processing
│   └── transcoder/          # FFmpeg audio transcoding and segmentation
├── pwa-client/              # React PWA with Vite (planned)
├── docker-compose.yml       # ✅ Service orchestration
├── env.example             # Environment configuration template
├── project_description.json # ✅ Detailed project specifications
├── project_plan.md         # ✅ Implementation roadmap
└── README.md               # ✅ This file
```

## 🔄 Processing Pipeline

### Current Workflow (Phase 3 Complete)

```
📝 Book Upload (API)
    ↓ (Immediate Response)
🔄 Background Task Triggered
    ↓ (Redis Queue)
📨 Ingest Service Processing
    ↓ (Text Extraction)
💾 Storage Service Update
    ↓ (Status Update)
📊 Real-time Status: SEGMENTING (25%)
```

### Status Progression

| Status | Progress | Description |
|--------|----------|-------------|
| `PENDING` | 0% | Book submitted, awaiting processing |
| `PROCESSING` | 5% | Background pipeline initiated |
| `EXTRACTING` | 10% | Text extraction in progress |
| `SEGMENTING` | 25% | Text extracted, chunking initiated |
| `GENERATING_AUDIO` | 50% | TTS processing (future phase) |
| `TRANSCODING` | 75% | Audio format conversion (future phase) |
| `COMPLETED` | 100% | Ready for streaming |
| `FAILED` | - | Error occurred, check error_message |

### Background Processing

The API service includes a background task manager (`background_tasks.py`) that:

- **Monitors Progress**: Continuously checks Redis queues for completion notifications
- **Updates Status**: Real-time database updates with progress percentages
- **Handles Errors**: Propagates errors from processing services to the API
- **Manages Lifecycle**: Proper startup/shutdown of background monitoring tasks

### Inter-Service Communication

- **API → Redis**: Task queuing with JSON payloads
- **Ingest → Storage**: HTTP POST for text storage
- **Ingest → Redis**: Completion notifications
- **Redis → API**: Status updates via queue monitoring

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

- `API_KEY`: Authentication secret for API access (default: "default-dev-key")
- `DATABASE_PATH`: SQLite database location (default: "/data/meta/audiobooks.db")
- `REDIS_URL`: Redis connection string (default: "redis://localhost:6379")
- `CORS_ORIGINS`: Allowed origins for CORS (default: "http://localhost:3000")

### Current Database Schema

**Books Table:**
```sql
CREATE TABLE books (
    id TEXT PRIMARY KEY,              -- UUID
    title TEXT NOT NULL,              -- Book title
    format TEXT NOT NULL,             -- pdf, epub, txt
    status TEXT DEFAULT 'pending',    -- Processing status
    percent_complete REAL DEFAULT 0.0, -- Progress percentage
    error_message TEXT,               -- Error details if failed
    file_path TEXT,                   -- Original file location
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_chunks INTEGER DEFAULT 0    -- Number of audio chunks
);
```

**Chunks Table:**
```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,            -- Foreign key to books
    seq INTEGER NOT NULL,             -- Sequence number
    duration_s REAL NOT NULL,         -- Duration in seconds
    file_path TEXT NOT NULL,          -- Audio file location
    file_size INTEGER,                -- File size in bytes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (book_id, seq)
);
```

## 🔌 API Endpoints

### Current Implementation Status

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/health` | GET | ✅ **IMPLEMENTED** | Service health check with database connectivity |
| `/` | GET | ✅ **IMPLEMENTED** | API information and version |
| `/docs` | GET | ✅ **IMPLEMENTED** | Interactive API documentation |
| `/api/v1/books` | POST | ✅ **IMPLEMENTED** | Submit new book for processing with file upload |
| `/api/v1/books/{book_id}/status` | GET | ✅ **IMPLEMENTED** | Check processing status with progress tracking |
| `/api/v1/books/{book_id}/chunks` | GET | ✅ **IMPLEMENTED** | List available audio chunks with metadata |
| `/api/v1/books/{book_id}/chunks/{seq}` | GET | ✅ **IMPLEMENTED** | Stream audio chunk files |

### Data Models

**Request/Response Models:**
- `BookSubmissionRequest`: File upload with title and format
- `BookResponse`: Book creation response with ID and status
- `BookStatusResponse`: Detailed status with progress and error info
- `ChunkInfo`: Audio chunk metadata with duration and URL
- `ChunkListResponse`: List of available chunks with totals
- `ErrorResponse`: Standardized error format

**Enums:**
- `BookFormat`: PDF, EPUB, TXT
- `BookStatus`: PENDING, PROCESSING, EXTRACTING, SEGMENTING, GENERATING_AUDIO, TRANSCODING, COMPLETED, FAILED

### Authentication

All API endpoints (except health checks) require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/v1/books
```

## 🧪 Testing

### Current Testing Status

✅ **Data Models**: All Pydantic models and database operations validated
✅ **Database**: SQLite schema creation and CRUD operations tested
✅ **Container**: Docker build and deployment working
✅ **Health Checks**: API, database, and pipeline connectivity verified
✅ **File Upload**: Book submission with validation and storage tested
✅ **Authentication**: API key protection on all endpoints verified
✅ **Error Handling**: 404, 400, 401, and 413 responses tested
✅ **File Storage**: Organized directory structure and file persistence verified
✅ **Background Processing**: Async pipeline monitoring and task management tested
✅ **Service Integration**: API ↔ Ingest ↔ Storage communication verified
✅ **Status Updates**: Real-time progress tracking from PENDING to SEGMENTING tested
✅ **Queue Processing**: Redis-based task queuing and completion notifications working

### Manual Testing

```bash
# Start the complete processing pipeline
docker-compose up -d api storage redis ingest

# Check health (includes pipeline status)
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"api","redis":"healthy","database":"healthy","pipeline":{"redis":"healthy","database":"healthy","pipeline":"ready"},"version":"1.0.0"}

# Test complete processing pipeline workflow
echo "This is a sample audiobook content for testing the processing pipeline." > sample.txt

# Submit a book
BOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer default-dev-key" \
  -F "title=Pipeline Test Book" \
  -F "format=txt" \
  -F "file=@sample.txt")

# Extract book ID (requires jq: sudo apt install jq)
BOOK_ID=$(echo $BOOK_RESPONSE | jq -r '.book_id')
echo "Book ID: $BOOK_ID"

# Check immediate status (should be PROCESSING or EXTRACTING)
echo "Immediate status:"
curl -s -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/$BOOK_ID/status | jq .

# Wait and check status progression
sleep 5
echo "Status after processing:"
curl -s -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/$BOOK_ID/status | jq .

# Verify background processing logs
echo "API processing logs:"
docker-compose logs api --tail=10 | grep "background_tasks"

echo "Ingest service logs:"
docker-compose logs ingest --tail=10

# List chunks (will be empty until full pipeline is complete)
curl -s -H "Authorization: Bearer default-dev-key" \
  http://localhost:8000/api/v1/books/$BOOK_ID/chunks | jq .

# Verify shared file storage
echo "Files in API container:"
docker exec evocable-api-1 ls -la /data/text/$BOOK_ID/ 2>/dev/null || echo "Directory not found"

echo "Files in Ingest container:"
docker exec evocable-ingest-1 ls -la /data/text/$BOOK_ID/ 2>/dev/null || echo "Directory not found"

# Check Redis queue status
echo "Redis queue lengths:"
docker exec evocable-redis-1 redis-cli llen ingest_queue
docker exec evocable-redis-1 redis-cli llen ingest_completed
```

## 📊 Monitoring

### Health Checks

- **API Service**: `GET /health` - Includes Redis and database connectivity
- **Database**: SQLite file creation and table initialization
- **Container**: Proper permissions and data directory setup

### Logging

```bash
# View API service logs
docker-compose logs -f api

# View all service logs
docker-compose logs -f
```

## 🔒 Security

- ✅ API key authentication for protected endpoints
- ✅ CORS configuration for client access
- ✅ Non-root container user with proper permissions
- ✅ Environment-based configuration

## 🚀 Next Steps

### Phase 4: Complete Processing Pipeline (Current Sprint)

1. **Segmenter Service Integration**
   - Text chunking with 800-character segments
   - SSML markup generation for TTS optimization
   - Metadata extraction and storage

2. **TTS Worker Service Integration**
   - FastPitch + HiFiGAN model integration
   - GPU-accelerated audio generation
   - Batch processing optimization

3. **Transcoder Service Integration**
   - FFmpeg-based audio format conversion
   - Opus@32kbps encoding for streaming
   - Audio chunk segmentation and metadata

### Development Workflow

```bash
# Start development environment
docker-compose up -d

# Make changes to API code
# ... edit files ...

# Rebuild and restart API service
docker-compose up --build -d api

# Test changes
curl http://localhost:8000/health
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the phase-based development plan
4. Test thoroughly with Docker
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

[License information]

## 🆘 Support

- [Issues](https://github.com/your-repo/issues)
- [Project Plan](project_plan.md)
- [API Reference](http://localhost:8000/docs) 