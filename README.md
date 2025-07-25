# Evocable - Audiobook Generation Backend

A comprehensive document-to-audiobook conversion system built with microservices architecture. Provides a robust API for converting PDF, EPUB, and TXT documents into high-quality streaming audiobooks using advanced text-to-speech technology.

## 🚀 Project Overview

Evocable Backend is a production-ready microservices system that processes documents into streaming audiobooks with real-time status updates. Built for scalability and performance with Docker orchestration, it provides a complete API for external client applications.

### Key Features
- **Document Processing**: PDF, EPUB, and TXT to audiobook conversion with OCR fallback
- **High-Quality TTS**: Coqui TTS with Tacotron2-DDC model for natural speech synthesis
- **Advanced Audio Streaming**: Chunk-based streaming API with seeking support
- **Real-time Status Updates**: Live processing progress with detailed status information
- **RESTful API**: Complete API for external client integration
- **Secure Authentication**: API key-based authentication system
- **Scalable Architecture**: Microservices with Redis message queuing

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: FastAPI with Python microservices
- **Message Queue**: Redis for service coordination
- **Text Processing**: spaCy for segmentation, pdfplumber/ebooklib for extraction
- **Text-to-Speech**: Coqui TTS with Tacotron2-DDC model
- **Audio Processing**: FFmpeg for WAV to Opus transcoding
- **Storage**: SQLite for metadata, filesystem for audio chunks
- **Deployment**: Docker Compose orchestration

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  External       │    │   FastAPI API   │    │  Redis Message  │
│  Clients        │◄──►│   Gateway       │◄──►│     Broker      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌────▼─────┐
        │   Storage    │ │   Ingest    │ │Segmenter │
        │   Service    │ │  Service    │ │ Service  │
        └──────────────┘ └─────────────┘ └──────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────────────────┐
        │ TTS Worker   │ │    Transcoder           │
        │ (GPU-based)  │ │    Service              │
        └──────────────┘ └─────────────────────────┘
```

## 📁 Project Structure

```
evocable-backend/
├── services/                   # Backend microservices
│   ├── api/                   # FastAPI gateway service
│   ├── storage/               # Data storage and metadata
│   ├── ingest/                # Document text extraction
│   ├── segmenter/             # Text chunking and SSML
│   ├── tts-worker/            # Text-to-speech processing
│   └── transcoder/            # Audio format conversion
├── tests/                     # Backend API tests
├── plans/                     # Project documentation
├── nginx/                     # Reverse proxy configuration
├── docker-compose.yml         # Service orchestration
└── .cursor/rules/             # Development rules
```

## 🚀 Quick Start

### Prerequisites
```bash
# Required tools
- Docker 24+ with Docker Compose
- Git 2.30+
- NVIDIA GPU with CUDA support (for TTS)
```

### Installation & Setup
```bash
# 1. Clone the repository
git clone <repository-url>
cd evocable-backend

# 2. Environment configuration
cp env.example .env
# Edit .env with your API_KEY and configuration

# 3. Start all services
docker-compose up -d

# 4. Verify services are running
docker-compose ps

# 5. Access the API
# API Gateway: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Development Setup
```bash
# Start services in development mode
docker-compose up --build

# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f api

# Stop all services
docker-compose down

# Reset all data
docker-compose down -v
```

## 🔧 Services Overview

### API Gateway (services/api/)
- **FastAPI** with async request handling
- **Authentication** via API key validation
- **WebSocket Support** for real-time updates
- **Background Tasks** for processing coordination
- **RESTful Endpoints** for all client interactions

### Storage Service (services/storage/)
- **SQLite Database** for metadata management
- **File System Management** for audio chunks
- **Book State Tracking** throughout processing pipeline
- **Chunk Duration Calculation** and indexing

### Document Ingestion (services/ingest/)
- **PDF Processing** via pdfplumber with OCR fallback
- **EPUB Processing** via ebooklib and BeautifulSoup
- **TXT Processing** with automatic encoding detection
- **Tesseract OCR** for image-based PDF content

### Text Segmentation (services/segmenter/)
- **spaCy English Model** for sentence tokenization
- **Smart Chunking** to ~800 character segments
- **SSML Generation** with pause and emphasis tags
- **Context-Aware Splitting** to preserve meaning

### TTS Worker (services/tts-worker/)
- **Coqui TTS** with Tacotron2-DDC model
- **GPU Acceleration** via CUDA (RTX 3090)
- **High-Quality Output** at 24kHz 16-bit WAV
- **Singleton Model Loading** for efficiency

### Audio Transcoding (services/transcoder/)
- **FFmpeg Processing** for format conversion
- **Opus Encoding** at 32kbps in Ogg container
- **Fixed Segment Duration** (3.14 seconds)
- **Optimized for Streaming** with low latency

## 🎵 Audio Processing Pipeline

```
Document Upload → Text Extraction → Segmentation → TTS Processing → Transcoding → Streaming
     ↓                ↓              ↓             ↓               ↓           ↓
  [Ingest]      [Segmenter]    [TTS-Worker]   [Transcoder]   [Storage]   [API Client]
```

1. **Upload**: Client uploads PDF/EPUB/TXT via API
2. **Extraction**: Document text extracted with fallback to OCR
3. **Segmentation**: Text split into ~800 character chunks with SSML
4. **TTS**: High-quality speech synthesis using Tacotron2-DDC
5. **Transcoding**: WAV converted to streaming-optimized Opus
6. **Delivery**: Client streams audio via API endpoints

## 📡 API Reference

### Authentication
All API requests require authentication via API key:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/v1/books
```

### Core Endpoints

#### **Submit Document for Processing**
```http
POST /api/v1/books
Content-Type: multipart/form-data
Authorization: Bearer YOUR_API_KEY

# Form fields:
# - title: string (optional)
# - file: PDF/EPUB/TXT file
# - format: string (pdf|epub|txt)
```

**Response:**
```json
{
  "book_id": "uuid-string",
  "status": "processing",
  "title": "Document Title"
}
```

#### **Check Processing Status**
```http
GET /api/v1/books/{book_id}/status
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "book_id": "uuid-string",
  "status": "processing|completed|failed",
  "percent_complete": 75,
  "current_step": "tts_processing",
  "error_message": null,
  "total_chunks": 10,
  "completed_chunks": 7
}
```

#### **List Audio Chunks**
```http
GET /api/v1/books/{book_id}/chunks
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "book_id": "uuid-string",
  "total_duration_s": 3600.0,
  "chunks": [
    {
      "seq": 0,
      "duration_s": 3.14,
      "url": "/api/v1/books/{book_id}/chunks/0"
    },
    // ... more chunks
  ]
}
```

#### **Stream Audio Chunk**
```http
GET /api/v1/books/{book_id}/chunks/{seq}
Authorization: Bearer YOUR_API_KEY
Accept: audio/ogg
```

**Response:** Binary Opus audio data in Ogg container

#### **List All Books**
```http
GET /api/v1/books
Authorization: Bearer YOUR_API_KEY
```

**Response:**
```json
{
  "books": [
    {
      "id": "uuid-string",
      "title": "Book Title",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "total_duration_s": 3600.0
    }
    // ... more books
  ]
}
```

### WebSocket Status Updates
Connect to real-time processing updates:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/books/{book_id}');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log('Processing update:', status);
};
```

## 🔧 Client Integration

### CORS Configuration
The API supports CORS for web clients. Configure allowed origins in environment:
```bash
# .env
CORS_ORIGINS=http://localhost:3000,https://yourapp.com
```

Or configure programmatically:
```python
# services/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Key Management
Generate secure API keys for your clients:
```bash
# Generate a secure API key
openssl rand -hex 32

# Set in environment
API_KEY=your-secure-api-key-here
```

### Error Handling
The API returns standard HTTP status codes:
- **200**: Success
- **202**: Accepted (processing started)
- **400**: Bad Request (invalid input)
- **401**: Unauthorized (invalid API key)
- **404**: Not Found (book/chunk not found)
- **500**: Internal Server Error

Example error response:
```json
{
  "detail": "Invalid file format. Supported: PDF, EPUB, TXT",
  "error_code": "INVALID_FORMAT"
}
```

## 🧪 Testing

### Current Test Coverage
- **Backend API Tests**: Comprehensive Python test suite in `tests/`
- **Service Integration**: Docker Compose health checks
- **End-to-End Testing**: Complete processing pipeline validation

### Running Tests
```bash
# Backend API tests
cd tests/
python run_tests.py

# Individual service testing
docker-compose exec api python -m pytest
docker-compose exec storage python -m pytest

# Health check all services
docker-compose ps
```

## 🔧 Configuration

### Environment Variables
```bash
# Core Configuration
API_KEY=your-secure-api-key-here
REDIS_URL=redis://redis:6379

# Service URLs (Docker internal)
STORAGE_URL=http://storage:8001

# TTS Configuration
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
CHUNK_SIZE_CHARS=800
SEGMENT_DURATION=3.14
OPUS_BITRATE=32k

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourapp.com
```

### Docker Compose Services
```yaml
# View complete configuration
cat docker-compose.yml

# Key services:
# - api: FastAPI gateway (port 8000)
# - storage: Data management (port 8001)  
# - redis: Message broker (port 6379)
# - ingest: Document processing
# - segmenter: Text chunking
# - tts-worker: Speech synthesis (GPU)
# - transcoder: Audio conversion
```

## 🚀 Deployment

### Production Deployment
```bash
# Build production images
docker-compose -f docker-compose.yml build

# Start in production mode
docker-compose -f docker-compose.yml up -d

# Monitor logs
docker-compose logs -f
```

### Scaling Considerations
- **TTS Worker**: Requires NVIDIA GPU with CUDA
- **Storage**: Uses local filesystem, consider network storage for scale
- **Redis**: Single instance sufficient for current scale (10 users)
- **API Gateway**: Can be horizontally scaled behind load balancer

### Reverse Proxy Setup
Use nginx for production deployment:
```bash
# Copy nginx configuration
cp nginx/default.conf /etc/nginx/sites-available/evocable

# Enable site
ln -s /etc/nginx/sites-available/evocable /etc/nginx/sites-enabled/

# Restart nginx
systemctl restart nginx
```

## 🛠️ Development

### Adding New Features
1. **API Endpoints**: Extend `services/api/main.py`
2. **New Services**: Create new service directory with Dockerfile
3. **Testing**: Add tests to `tests/` directory
4. **Documentation**: Update API documentation

### Service Communication
- **REST API**: External clients ↔ API Gateway
- **Redis Queues**: Inter-service messaging
- **HTTP**: Service-to-service communication
- **File System**: Shared volumes for data

### Monitoring & Debugging
```bash
# Service health
docker-compose ps

# View all logs
docker-compose logs -f

# Service-specific logs
docker-compose logs -f tts-worker

# Enter service container
docker-compose exec api bash

# Redis monitoring
docker-compose exec redis redis-cli monitor
```

## 📊 Performance

### Current Specifications
- **Hardware**: Single PC with NVIDIA RTX 3090
- **Concurrent Users**: Up to 10 users, 1-2 concurrent streams
- **TTS Processing**: ~2-3x real-time on RTX 3090
- **Audio Quality**: 24kHz synthesis → 32kbps Opus streaming
- **Segment Duration**: 3.14 seconds for optimal streaming

### Optimization Features
- **GPU Acceleration**: TTS processing on CUDA
- **Chunk-based Streaming**: Immediate playback start
- **Audio Compression**: Opus codec for bandwidth efficiency
- **Caching**: Redis for metadata and processing state

## 📞 Support & Documentation

### Additional Documentation
- **[Design Requirements](plans/pwa_design_requirements_plan.md)** - Complete project scope and requirements
- **[Component Interfaces](plans/component_interfaces.md)** - Development interfaces and contracts  
- **[Testing Strategy](plans/testing_strategy.md)** - Comprehensive testing approach
- **[UI Wireframes](plans/pwa_wireframes.md)** - Interface designs (for reference)

### API Documentation
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **ReDoc**: `http://localhost:8000/redoc`

### Getting Help
- **Issues**: Use GitHub Issues for bug reports
- **Documentation**: Check `plans/` directory for detailed guides
- **Logs**: Use `docker-compose logs` for debugging
- **API Testing**: Use the interactive documentation at `/docs`

---

## 🎯 Project Status

**Current Phase**: Production-ready backend API
- ✅ **Document Processing**: Full PDF/EPUB/TXT support with OCR
- ✅ **High-Quality TTS**: Tacotron2-DDC model integration
- ✅ **Streaming Audio**: Opus-encoded chunk-based delivery
- ✅ **RESTful API**: Complete API for external client integration
- ✅ **Authentication**: Secure API key-based access
- ✅ **Real-time Updates**: Live processing status via REST and WebSocket
- ✅ **Production Ready**: Docker orchestration with health checks
- ✅ **Comprehensive Testing**: Backend API test coverage

## 🔗 Related Projects

- **Evocable PWA**: Frontend client application (separate repository)
- **Mobile Apps**: iOS/Android clients can integrate via REST API
- **Third-party Integrations**: Any client supporting HTTP and audio streaming

This backend system provides a robust, scalable foundation for audiobook generation that can support multiple client applications through its comprehensive REST API. 