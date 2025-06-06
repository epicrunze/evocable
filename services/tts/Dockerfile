FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04
WORKDIR /src
RUN apt-get update && apt-get install -y python3.11 python3.11-venv python3-pip git && rm -rf /var/lib/apt/lists/*
COPY src/tts.py ./
RUN python3.11 -m pip install --no-cache-dir TTS==0.22.0
# Download a default TTS model (English)
RUN python3.11 -c "from TTS.utils.manage import ModelManager; ModelManager().download_model('tts_models/en/ljspeech/tacotron2-DDC')"
CMD ["python3.11", "tts.py"] 