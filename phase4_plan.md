# Phase 4: Complete Processing Pipeline Implementation Plan

## 🎯 Overview

Phase 4 completes the audiobook processing pipeline by implementing the three remaining services:
1. **Segmenter Service**: Text chunking and SSML generation
2. **TTS Worker Service**: Text-to-speech audio generation
3. **Transcoder Service**: Audio format conversion and streaming preparation

**Current State**: Text extraction pipeline (API → Ingest → Storage) is complete and functional.
**Goal**: Complete end-to-end pipeline from text upload to streaming audio chunks.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Text Upload   │───►│  Text Extract   │───►│  Text Storage   │
│   (API)         │    │  (Ingest)       │    │  (Storage)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Audio Chunks   │◄───│  Audio Convert  │◄───│  Text Segment   │
│  (API Serve)    │    │  (Transcoder)   │    │  (Segmenter)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                       │
                                │                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  WAV Storage    │◄───│  TTS Generate   │
                       │  (Storage)      │    │  (TTS Worker)   │
                       └─────────────────┘    └─────────────────┘
```

## 📋 Implementation Plan

### **Phase 4.1: Segmenter Service (Days 1-3)**

#### **Objective**: Transform extracted text into TTS-ready chunks with SSML markup

#### **Technical Specifications**
- **Input**: Raw text from storage service
- **Output**: SSML-marked chunks (800 characters max)
- **Processing**: spaCy sentence tokenization + intelligent chunking
- **Storage**: Chunk metadata in database, SSML files in storage

#### **Implementation Steps**

**Day 1: Core Segmentation Logic**
1. **Install Dependencies**
   ```bash
   # Add to requirements.txt
   spacy>=3.7.0
   spacy-transformers>=1.3.0
   ```

2. **Text Segmentation Engine**
   ```python
   class TextSegmenter:
       def __init__(self):
           self.nlp = spacy.load("en_core_web_sm")
           self.max_chunk_size = 800
       
       def segment_text(self, text: str) -> List[TextChunk]:
           # Sentence tokenization
           # Intelligent chunking (avoid mid-sentence breaks)
           # SSML markup generation
   ```

3. **SSML Generation**
   - Sentence boundaries → `<s>` tags
   - Paragraph breaks → `<break time="1s"/>`
   - Punctuation handling for natural pauses

**Day 2: Queue Processing & Storage Integration**
1. **Redis Queue Processing**
   ```python
   async def process_segmentation_queue():
       # Listen to segment_queue
       # Process text segmentation
       # Store SSML chunks
       # Update database metadata
       # Trigger TTS queue
   ```

2. **Storage Service Integration**
   - GET text from storage service
   - POST SSML chunks to storage service
   - Update book metadata with chunk count

3. **Database Schema Updates**
   ```sql
   -- Add to chunks table
   ALTER TABLE chunks ADD COLUMN ssml_path TEXT;
   ALTER TABLE chunks ADD COLUMN text_content TEXT;
   ```

**Day 3: Testing & Error Handling**
1. **Unit Tests**
   - Text segmentation accuracy
   - SSML markup validation
   - Chunk size constraints
   - Edge cases (very short/long texts)

2. **Integration Tests**
   - End-to-end: text → segments → SSML
   - Queue processing reliability
   - Storage service communication

3. **Error Handling**
   - spaCy model loading failures
   - Text processing errors
   - Storage service timeouts

#### **Key Technical Decisions**

**🔍 Decision Point 1: Chunking Strategy**
- **Option A**: Fixed 800-character chunks (simple, may break sentences)
- **Option B**: Sentence-aware chunking (complex, better quality)
- **Recommendation**: Option B with fallback to Option A for edge cases

**🔍 Decision Point 2: SSML Complexity**
- **Basic**: `<s>` tags and `<break>` elements only
- **Advanced**: Emphasis, rate, pitch adjustments
- **Recommendation**: Start with basic, expand based on TTS model capabilities

### **Phase 4.2: TTS Worker Service (Days 4-8)**

#### **Objective**: Convert SSML chunks to high-quality WAV audio files

#### **Technical Specifications**
- **Input**: SSML chunks from segmenter
- **Output**: WAV files (22kHz, 16-bit, mono)
- **Model**: TTS engine (see decision points below)
- **Processing**: GPU-accelerated batch processing
- **Storage**: WAV files in shared volume

#### **Implementation Steps**

**Day 4: TTS Engine Selection & Setup**

**🔍 Critical Decision: TTS Engine Choice**

**Option A: Coqui TTS (Recommended)**
```python
# Pros: Open source, good quality, easier deployment
# Cons: Newer, less documentation
pip install coqui-tts
```

**Option B: FastPitch + HiFiGAN (Original Plan)**
```python
# Pros: High quality, well-documented
# Cons: Complex setup, NVIDIA-specific
# Requires: NVIDIA NeMo toolkit
```

**Option C: Tortoise TTS**
```python
# Pros: Very high quality, natural speech
# Cons: Extremely slow, high memory usage
```

**Recommendation**: Start with **Coqui TTS** for faster development, add FastPitch option later.

**Day 5: TTS Processing Pipeline**
1. **Model Loading & Initialization**
   ```python
   class TTSProcessor:
       def __init__(self):
           self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
           self.device = "cuda" if torch.cuda.is_available() else "cpu"
       
       async def generate_audio(self, ssml_text: str) -> bytes:
           # SSML preprocessing
           # TTS generation
           # Audio post-processing
   ```

2. **Batch Processing Optimization**
   - Process multiple chunks in parallel
   - GPU memory management
   - Audio quality consistency

**Day 6: Queue Processing & Storage**
1. **Redis Queue Integration**
   ```python
   async def process_tts_queue():
       # Listen to tts_queue
       # Load SSML chunks
       # Generate WAV audio
       # Store to wav_data volume
       # Update database metadata
       # Trigger transcoder queue
   ```

2. **Audio File Management**
   - Consistent naming convention
   - File size optimization
   - Metadata extraction (duration, sample rate)

**Day 7: GPU Resource Management**
1. **Memory Management**
   - Model loading/unloading strategies
   - Batch size optimization based on available GPU memory
   - Error recovery for OOM conditions

2. **Performance Optimization**
   - Audio caching for repeated text
   - Concurrent processing limits
   - Resource monitoring and alerting

**Day 8: Testing & Quality Assurance**
1. **Audio Quality Tests**
   - Listening tests with sample content
   - Audio analysis (frequency response, distortion)
   - Consistency across different text types

2. **Performance Tests**
   - Processing speed benchmarks
   - Memory usage profiling
   - GPU utilization monitoring

#### **Key Technical Decisions**

**🔍 Decision Point 3: Model Storage Strategy**
- **Build-time**: Download models during Docker build (larger images, faster startup)
- **Runtime**: Download models on first use (smaller images, slower startup)
- **Recommendation**: Build-time for production, runtime for development

**🔍 Decision Point 4: Voice Configuration**
- **Single Voice**: One consistent voice for all books
- **Multiple Voices**: Different voices for different books/genres
- **Recommendation**: Single voice initially, expand later

### **Phase 4.3: Transcoder Service (Days 9-11)**

#### **Objective**: Convert WAV files to streaming-optimized Opus audio chunks

#### **Technical Specifications**
- **Input**: WAV files from TTS worker
- **Output**: Opus-encoded Ogg segments (32kbps, 3.14s duration)
- **Tool**: FFmpeg for audio processing
- **Streaming**: HTTP-friendly chunk sizes and formats

#### **Implementation Steps**

**Day 9: FFmpeg Integration & Audio Processing**
1. **Audio Transcoding Pipeline**
   ```python
   class AudioTranscoder:
       def __init__(self):
           self.segment_duration = 3.14  # seconds
           self.opus_bitrate = "32k"
       
       async def transcode_wav_to_opus(self, wav_path: Path) -> List[AudioChunk]:
           # FFmpeg command construction
           # Segmentation and encoding
           # Metadata extraction
   ```

2. **FFmpeg Command Optimization**
   ```bash
   ffmpeg -i input.wav \
     -c:a libopus \
     -b:a 32k \
     -frame_duration 20 \
     -application voip \
     -f segment \
     -segment_time 3.14 \
     -segment_format ogg \
     output_%03d.ogg
   ```

**Day 10: Queue Processing & Metadata Management**
1. **Redis Queue Integration**
   ```python
   async def process_transcoding_queue():
       # Listen to transcode_queue
       # Load WAV files
       # Transcode to Opus segments
       # Store to segment_data volume
       # Update database with chunk metadata
       # Mark book as COMPLETED
   ```

2. **Database Updates**
   ```python
   # Update chunks table with final metadata
   def update_chunk_metadata(book_id: str, chunks: List[AudioChunk]):
       for i, chunk in enumerate(chunks):
           db.create_chunk(
               book_id=book_id,
               seq=i,
               duration_s=chunk.duration,
               file_path=chunk.path,
               file_size=chunk.size
           )
   ```

**Day 11: Quality Control & Testing**
1. **Audio Quality Validation**
   - Opus encoding quality verification
   - Segment boundary analysis
   - Playback continuity testing

2. **Integration Testing**
   - End-to-end pipeline testing
   - Error handling and recovery
   - Performance benchmarking

#### **Key Technical Decisions**

**🔍 Decision Point 5: Segment Duration**
- **3.14 seconds**: Good balance of quality and streaming efficiency
- **Alternative**: 2-5 second range based on content type
- **Recommendation**: Stick with 3.14s, make configurable

**🔍 Decision Point 6: Audio Format**
- **Opus in Ogg**: Excellent compression, wide browser support
- **Alternative**: MP3 for broader compatibility
- **Recommendation**: Opus for quality, add MP3 fallback if needed

### **Phase 4.4: Integration & Testing (Days 12-14)**

#### **Objective**: Complete end-to-end pipeline integration and comprehensive testing

#### **Implementation Steps**

**Day 12: Pipeline Orchestration**
1. **Update Background Task Manager**
   ```python
   # Add to background_tasks.py
   async def _check_segmentation_completion(self):
       # Handle segmenter → TTS transition
   
   async def _check_tts_completion(self):
       # Handle TTS → transcoder transition
   
   async def _check_transcoding_completion(self):
       # Handle final completion → COMPLETED status
   ```

2. **Status Progression Updates**
   - SEGMENTING (25%) → GENERATING_AUDIO (50%)
   - GENERATING_AUDIO (50%) → TRANSCODING (75%)
   - TRANSCODING (75%) → COMPLETED (100%)

**Day 13: End-to-End Testing**
1. **Complete Pipeline Test**
   ```bash
   # Upload book → Stream audio chunks
   curl -X POST /api/v1/books \
     -F "title=E2E Test" \
     -F "format=txt" \
     -F "file=@test_book.txt"
   
   # Monitor status progression
   # Verify audio chunk generation
   # Test streaming playback
   ```

2. **Performance Testing**
   - Processing time benchmarks
   - Resource utilization monitoring
   - Concurrent processing limits

**Day 14: Error Handling & Documentation**
1. **Comprehensive Error Handling**
   - Service failure recovery
   - Partial processing resume
   - User-friendly error messages

2. **Documentation Updates**
   - API documentation
   - Service configuration guides
   - Troubleshooting guides

## 🔧 Configuration & Environment

### **Environment Variables**
```bash
# Segmenter Service
SPACY_MODEL=en_core_web_sm
CHUNK_SIZE_CHARS=800
SEGMENT_QUEUE=segment_queue

# TTS Worker Service
TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
TTS_DEVICE=cuda
TTS_BATCH_SIZE=4
WAV_SAMPLE_RATE=22050

# Transcoder Service
OPUS_BITRATE=32k
SEGMENT_DURATION=3.14
TRANSCODE_QUEUE=transcode_queue
```

### **Docker Compose Updates**
```yaml
# Enable TTS worker service
tts-worker:
  build: ./services/tts-worker
  runtime: nvidia  # For GPU support
  environment:
    NVIDIA_VISIBLE_DEVICES: all
  volumes:
    - wav_data:/data/wav
    - text_data:/data/text:ro
```

## 📊 Success Metrics

### **Functional Requirements**
- [ ] Complete text-to-audio pipeline working
- [ ] Audio quality suitable for audiobook consumption
- [ ] Streaming-ready chunk generation
- [ ] Real-time status updates throughout pipeline
- [ ] Error handling and recovery mechanisms

### **Performance Requirements**
- [ ] Processing speed: <5 minutes per 1000 words
- [ ] Audio quality: Clear, natural speech
- [ ] File size: <50MB per hour of audio
- [ ] Concurrent processing: 3+ books simultaneously
- [ ] System stability: 24/7 operation capability

### **Technical Requirements**
- [ ] All services containerized and orchestrated
- [ ] Comprehensive logging and monitoring
- [ ] Graceful error handling and recovery
- [ ] Database consistency and integrity
- [ ] API documentation and testing

## 🚨 Risk Mitigation

### **High-Risk Areas**
1. **TTS Model Complexity**: Start with simpler models, upgrade incrementally
2. **GPU Resource Management**: Implement proper memory management and fallbacks
3. **Audio Quality Consistency**: Extensive testing with diverse text types
4. **Processing Performance**: Optimize batch sizes and parallel processing

### **Fallback Strategies**
1. **TTS Fallback**: Cloud TTS APIs (Google, AWS) for development/testing
2. **GPU Fallback**: CPU-based processing for non-production environments
3. **Quality Fallback**: Lower bitrate/quality options for faster processing
4. **Processing Fallback**: Manual intervention tools for stuck pipelines

## 🎯 Next Steps After Phase 4

1. **Phase 5: PWA Client Development**
2. **Phase 6: Performance Optimization**
3. **Phase 7: Advanced Features** (multiple voices, speed control, bookmarks)
4. **Phase 8: Production Deployment** (monitoring, scaling, backup)

---

**Estimated Timeline**: 14 days
**Key Dependencies**: GPU hardware, TTS model selection, FFmpeg optimization
**Success Criteria**: Complete audiobook generation from text upload to streaming audio