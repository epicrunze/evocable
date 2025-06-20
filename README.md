# Audiobook Server

Convert user-provided PDF, EPUB, or TXT files into streamed English audiobook audio via a React PWA.

## 🎯 Project Overview

This system transforms text documents into high-quality audio streams using:
- **Text Extraction**: PDF (pdfplumber), EPUB (ebooklib), TXT with OCR fallback (Tesseract)
- **Text Processing**: spaCy sentence tokenization with 800-character chunking and SSML markup
- **Text-to-Speech**: FastPitch 2 + HiFiGAN on NVIDIA RTX 3090 for production-grade audio
- **Audio Streaming**: FFmpeg transcoding to Opus@32kbps in Ogg containers, segmented for streaming
- **Modern PWA**: React client with offline caching and real-time status updates

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
   cd audiobook-server
   cp env.example .env
   # Edit .env with your API_KEY and other settings
   ```

2. **Start the system**:
   ```bash
   docker compose up -d
   ```

3. **Access the application**:
   - PWA Client: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - Storage Service: http://localhost:8001/health

### Development Setup

1. **Install pre-commit hooks**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Run tests**:
   ```bash
   # Python services
   docker compose exec api pytest
   docker compose exec storage pytest
   
   # Client
   cd pwa-client
   npm test
   ```

## 📁 Project Structure

```
audiobook-server/
├── services/
│   ├── api/              # FastAPI gateway and orchestration
│   ├── storage/          # Centralized metadata and file management
│   ├── ingest/           # Text extraction from PDF/EPUB/TXT
│   ├── segmenter/        # Text chunking and SSML generation
│   ├── tts-worker/       # FastPitch + HiFiGAN TTS processing
│   └── transcoder/       # FFmpeg audio transcoding and segmentation
├── pwa-client/           # React PWA with Vite
├── docker-compose.yml    # Service orchestration
├── env.example          # Environment configuration template
└── .github/workflows/   # CI/CD pipelines
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

- `API_KEY`: Authentication secret for API access
- `CHUNK_SIZE_CHARS`: Text chunk size for processing (default: 800)
- `SEGMENT_DURATION`: Audio segment duration in seconds (default: 3.14)
- `OPUS_BITRATE`: Audio compression bitrate (default: 32k)
- `MODEL_PATH`: TTS model storage location

### Service Configuration

Each service can be configured independently:

- **API**: CORS, authentication, rate limiting
- **Storage**: Database connection, file paths
- **Processing Services**: Queue names, batch sizes, timeouts
- **TTS Worker**: GPU settings, model parameters
- **Transcoder**: Audio quality, segment timing

## 🔌 API Endpoints

### Book Management

- `POST /api/v1/books` - Submit new book for processing
- `GET /api/v1/books/{book_id}/status` - Check processing status
- `GET /api/v1/books/{book_id}/chunks` - List available audio chunks
- `GET /api/v1/books/{book_id}/chunks/{seq}` - Stream audio chunk

### Storage Service

- `GET /health` - Service health check
- `POST /books` - Create book metadata
- `GET /books/{book_id}` - Retrieve book information
- `PUT /books/{book_id}/chunks` - Update chunk metadata

## 🧪 Testing

### Unit Tests

Each service includes comprehensive unit tests:

```bash
# Run all Python tests
docker compose exec api pytest
docker compose exec storage pytest
docker compose exec ingest pytest
docker compose exec segmenter pytest
docker compose exec tts-worker pytest
docker compose exec transcoder pytest

# Run client tests
cd pwa-client && npm test
```

### Integration Tests

End-to-end testing with sample documents:

```bash
# Test complete pipeline
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@sample.pdf" \
  -F "title=Test Book"
```

## 📊 Monitoring

### Health Checks

All services expose health endpoints:

- API: `GET /health`
- Storage: `GET /health`
- Processing services: Internal health checks

### Logging

Structured logging with configurable levels:

```bash
# View service logs
docker compose logs -f api
docker compose logs -f storage
docker compose logs -f tts-worker
```

## 🔒 Security

- API key authentication for all endpoints
- CORS configuration for client access
- Read-only volume mounts where appropriate
- Environment-based configuration

## 🚀 Deployment

### Production

1. Set production environment variables
2. Configure external storage volumes
3. Set up reverse proxy (nginx/traefik)
4. Configure SSL certificates
5. Set up monitoring and alerting

### Scaling

- Horizontal scaling of processing services
- Redis cluster for high availability
- External database for metadata
- CDN for audio file distribution

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the full test suite
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

[License information]

## 🆘 Support

- [Issues](https://github.com/your-repo/issues)
- [Documentation](docs/)
- [API Reference](http://localhost:8000/docs) 