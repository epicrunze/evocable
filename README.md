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

### 🔄 Phase 2: Core API Endpoints (IN PROGRESS)
- Book submission endpoint with file upload handling
- Status checking with real-time progress updates
- Audio chunk listing and streaming endpoints
- Service integration with processing pipeline

### ⏳ Phase 3: Service Integration (PLANNED)
- Ingest service communication for text extraction
- Processing pipeline orchestration
- Background task management

### ⏳ Phase 4: Error Handling & Validation (PLANNED)
- Comprehensive input validation
- Standardized error responses
- Logging and monitoring integration

### ⏳ Phase 5: Testing & Documentation (PLANNED)
- Unit and integration tests
- API documentation
- Performance optimization

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
# Test API health (includes database connectivity)
curl http://localhost:8000/health

# Test API root
curl http://localhost:8000/

# Test authenticated endpoint (placeholder)
curl -H "Authorization: Bearer default-dev-key" \
     http://localhost:8000/api/v1/books/test-123/status
```

## 📁 Project Structure

```
evocable/
├── services/
│   ├── api/                  # FastAPI gateway and orchestration
│   │   ├── main.py          # ✅ FastAPI app with auth & health checks
│   │   ├── models.py        # ✅ Pydantic models & database manager
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
| `/api/v1/books` | POST | 🔄 **PLACEHOLDER** | Submit new book for processing |
| `/api/v1/books/{book_id}/status` | GET | 🔄 **PLACEHOLDER** | Check processing status |
| `/api/v1/books/{book_id}/chunks` | GET | 🔄 **PLACEHOLDER** | List available audio chunks |
| `/api/v1/books/{book_id}/chunks/{seq}` | GET | 🔄 **PLACEHOLDER** | Stream audio chunk |

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
✅ **Health Checks**: API and database connectivity verified

### Manual Testing

```bash
# Test the API service
docker-compose up -d api redis

# Check health
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"api","redis":"healthy","database":"healthy","version":"1.0.0"}

# Test database operations inside container
docker exec evocable-api-1 python -c "
from models import DatabaseManager
db = DatabaseManager()
book_id = db.create_book('Test Book', 'pdf', '/tmp/test.pdf')
print(f'Created book: {book_id}')
book = db.get_book(book_id)
print(f'Retrieved book: {book}')
"
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

### Phase 2: Core API Endpoints (Next Sprint)

1. **Book Submission Endpoint**
   - File upload handling (multipart/form-data)
   - File validation and storage
   - Background processing initiation

2. **Status Checking Endpoint**
   - Real-time progress tracking
   - Error state handling
   - Database query optimization

3. **Audio Streaming Endpoints**
   - Chunk listing with metadata
   - Audio file serving with proper headers
   - Range request support for streaming

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