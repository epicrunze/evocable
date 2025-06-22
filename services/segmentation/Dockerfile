FROM python:3.11
WORKDIR /src
COPY src/segment.py ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir spacy
RUN python -m spacy download en_core_web_sm
CMD ["python", "segment.py"] 