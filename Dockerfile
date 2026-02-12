FROM python:3.11-slim

# 1. System Dependencies Install karo (Git zaroori hai)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Requirements copy aur install karo
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3. Bot ka poora code copy karo
COPY axl_music_bot /app/axl_music_bot

# 4. Environment Variables aur Start Command
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "axl_music_bot.main"]
