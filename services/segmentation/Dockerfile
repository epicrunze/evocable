FROM python:3.11
WORKDIR /src
COPY src/segment.py ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir spacy
CMD ["python", "segment.py"] 