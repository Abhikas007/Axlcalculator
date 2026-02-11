FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY axl_music_bot /app/axl_music_bot
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "axl_music_bot.main"]
