FROM python:3.11-slim

# Cài FFmpeg + các thứ cần thiết để cắt video
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài yt-dlp mới nhất (đỡ lỗi signature YouTube)
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app

# Copy và cài requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code
COPY . .

# Mở port
EXPOSE 10000

# Chạy server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
