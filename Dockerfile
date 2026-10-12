FROM python:3.11-slim

# Install system dependencies including FFmpeg for audio transcoding
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definitions and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and static assets
COPY core/ core/
COPY static/ static/
COPY main.py .

# Create downloads directory
RUN mkdir -p downloads

# Default port 8000, dynamically overridable by Render/Railway via $PORT
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
