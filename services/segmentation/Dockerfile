FROM python:3.10-slim
WORKDIR /src
COPY ../../src/segment.py ./
RUN pip install --no-cache-dir spacy ssml
CMD ["python", "segment.py"] 