FROM python:3.10-slim
WORKDIR /src
COPY ../../src/upload.py ./
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir awscli
RUN curl https://downloads.rclone.org/rclone-current-linux-amd64.zip -o rclone.zip \
    && unzip rclone.zip \
    && cp rclone-*-linux-amd64/rclone /usr/bin/ \
    && chmod +x /usr/bin/rclone \
    && rm -rf rclone*
CMD ["python", "upload.py"] 