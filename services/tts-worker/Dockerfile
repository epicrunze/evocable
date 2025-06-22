FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including audio libraries
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libsndfile1 \
    libsndfile1-dev \
    ffmpeg \
    espeak-ng \
    espeak-ng-data \
    libespeak-ng1 \
    libespeak-ng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data
RUN mkdir -p /data/wav

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app /data
USER app

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import asyncio; from main import TTSWorker; worker = TTSWorker(); print(asyncio.run(worker.health_check()))" || exit 1

# Run the application
CMD ["python", "main.py"] 