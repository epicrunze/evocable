FROM python:3.10-slim
WORKDIR /src
COPY ../../src/extract.py ./
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pdfplumber pytesseract azure-cognitiveservices-vision-computervision ebooklib beautifulsoup4 chardet
CMD ["python", "extract.py"] 