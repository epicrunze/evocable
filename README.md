# Evocable - Audiobook Generation System

A comprehensive document-to-audiobook conversion system built with microservices architecture. Transforms PDF, EPUB, and TXT documents into high-quality streaming audiobooks using advanced text-to-speech technology.

## 🚀 Project Overview

Evocable is a production-ready system that converts documents into streaming audiobooks with real-time processing status and advanced audio playback capabilities. Built for scalability and performance with a microservices architecture running on Docker.

### Key Features
- **Document Processing**: PDF, EPUB, and TXT to audiobook conversion with OCR fallback
- **High-Quality TTS**: Coqui TTS with Tacotron2-DDC model for natural speech synthesis
- **Advanced Audio Streaming**: Chunk-based streaming with seeking and cross-chunk navigation
- **Real-time Status Updates**: Live processing progress with detailed status information
- **Mobile-Responsive PWA**: Next.js frontend optimized for desktop and mobile
- **Secure Authentication**: API key-based authentication with persistent sessions
- **Scalable Architecture**: Microservices with Redis message queuing

## 🏗️ Architecture Overview

### Technology Stack
- **Frontend**: Next.js 15 with TypeScript, React Query, Zustand
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
│   Next.js PWA   │    │   FastAPI API   │    │  Redis Message  │
│   (Frontend)    │◄──►│   Gateway       │◄──►│     Broker      │
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
evocable/
├── pwa-client/                 # Next.js frontend application
│   ├── src/
│   │   ├── app/               # Next.js app router pages
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # API clients and utilities
│   │   └── types/             # TypeScript type definitions
│   ├── package.json
│   └── next.config.ts
├── services/                   # Backend microservices
│   ├── api/                   # FastAPI gateway service
│   ├── storage/               # Data storage and metadata
│   ├── ingest/                # Document text extraction
│   ├── segmenter/             # Text chunking and SSML
│   ├── tts-worker/            # Text-to-speech processing
│   └── transcoder/            # Audio format conversion
├── tests/                     # Backend API tests
├── plans/                     # Project documentation
├── docker-compose.yml         # Service orchestration
└── nginx/                     # Reverse proxy configuration
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
cd evocable

# 2. Environment configuration
cp env.example .env
# Edit .env with your API_KEY and configuration

# 3. Start all services
docker-compose up -d

# 4. Verify services are running
docker-compose ps

# 5. Access the application
# Frontend: http://localhost:3000
# API: http://localhost:8000
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

### Frontend (pwa-client/)
- **Next.js 15** with TypeScript and Tailwind CSS
- **React Query** for server state management
- **Zustand** for client state management
- **Advanced Audio Player** with cross-chunk seeking
- **Real-time Status Updates** via polling
- **Mobile-responsive Design** with PWA capabilities

**Available Commands:**
```bash
cd pwa-client/
npm run dev              # Development server
npm run build           # Production build
npm run start           # Production server
npm run lint            # Code linting
```

### API Gateway (services/api/)
- **FastAPI** with async request handling
- **Authentication** via API key validation
- **WebSocket Support** for real-time updates
- **Background Tasks** for processing coordination
- **RESTful Endpoints** for all client interactions

**Key Endpoints:**
- `POST /api/v1/books` - Submit document for processing
- `GET /api/v1/books/{book_id}/status` - Check processing status
- `GET /api/v1/books/{book_id}/chunks` - List audio chunks
- `GET /api/v1/books/{book_id}/chunks/{seq}` - Stream audio chunk

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
  [Ingest]      [Segmenter]    [TTS-Worker]   [Transcoder]   [Storage]   [API/Client]
```

1. **Upload**: Client uploads PDF/EPUB/TXT via drag-and-drop
2. **Extraction**: Document text extracted with fallback to OCR
3. **Segmentation**: Text split into ~800 character chunks with SSML
4. **TTS**: High-quality speech synthesis using Tacotron2-DDC
5. **Transcoding**: WAV converted to streaming-optimized Opus
6. **Delivery**: Client streams audio with advanced playback controls

## 🧪 Testing

### Current Test Coverage
- **Backend API Tests**: Comprehensive Python test suite in `tests/`
- **Service Integration**: Docker Compose health checks
- **Manual Testing**: Frontend user workflows

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

## 📱 Frontend Features

### Currently Implemented
- ✅ **API Key Authentication** with persistent sessions
- ✅ **Drag & Drop Upload** with file validation
- ✅ **Real-time Processing Status** with progress updates
- ✅ **Advanced Audio Player** with seeking and chunk navigation
- ✅ **Book Library** with search and management
- ✅ **Mobile-Responsive Design** optimized for all devices
- ✅ **Error Handling** with user-friendly messages

### PWA Features (Planned)
- 🔄 **Service Worker** for offline caching
- 🔄 **Background Sync** for processing when online
- 🔄 **Push Notifications** for processing completion
- 🔄 **Offline Playback** with downloaded chunks

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

# Development
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
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

## 🛠️ Development

### Adding New Features
1. **Frontend**: Work in `pwa-client/src/`
2. **Backend**: Extend `services/api/` or create new service
3. **Testing**: Add tests to `tests/` directory
4. **Documentation**: Update relevant files in `plans/`

### Service Communication
- **REST API**: Client ↔ API Gateway
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
- **[UI Wireframes](plans/pwa_wireframes.md)** - Detailed interface designs

### Getting Help
- **Issues**: Use GitHub Issues for bug reports
- **Documentation**: Check `plans/` directory for detailed guides
- **Logs**: Use `docker-compose logs` for debugging
- **API**: Access interactive docs at `http://localhost:8000/docs`

---

## 🎯 Project Status

**Current Phase**: Production-ready core functionality
- ✅ **Document Processing**: Full PDF/EPUB/TXT support with OCR
- ✅ **High-Quality TTS**: Tacotron2-DDC model integration
- ✅ **Streaming Audio**: Opus-encoded chunk-based delivery
- ✅ **Web Interface**: Complete Next.js PWA with advanced player
- ✅ **Authentication**: Secure API key-based access
- ✅ **Real-time Updates**: Live processing status
- 🔄 **PWA Features**: Service worker and offline capabilities (planned)
- 🔄 **Enhanced Testing**: Comprehensive frontend test coverage (planned)
- 🔄 **Monitoring**: Performance and error tracking (planned)

This system demonstrates a production-grade microservices architecture with modern web technologies, delivering high-quality audiobook generation with an intuitive user experience. 