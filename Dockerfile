FROM python:3.11-slim

# 1. Install System Dependencies (Added 'git' here)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python Requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy Bot Code
# (Agar aapka folder structure waisa hi hai jaisa pehle tha)
COPY axl_music_bot /app/axl_music_bot

ENV PYTHONUNBUFFERED=1

# 4. Start Command
CMD ["python", "-m", "axl_music_bot.main"]
