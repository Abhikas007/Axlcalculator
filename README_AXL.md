# AXL MUSIC BOT

This repository contains a scaffold for "AXL MUSIC BOT" — a Telegram voice-chat music bot. It is branded with "AXL MUSIC BOT created by - @figletaxl Dev - Figletaxl" and uses `!` as the default prefix.

Quick start

1. Copy `.env.sample` to `.env` and fill your `API_ID`, `API_HASH`, and `BOT_TOKEN`.
2. Build and run locally (requires `ffmpeg`):

```bash
python -m pip install -r requirements.txt
python -m axl_music_bot.main
```

Docker (Koyeb):

1. Push this repo to a Git provider (GitHub). 2. In Koyeb, create an app using Dockerfile build from this repo. Set environment variables in the Koyeb dashboard using the values from `.env.sample`.

Commands (examples):
- `!play <url or query>` — download & queue audio
- `!leave` — leave VC and clear queue
- `!effects <preset>` — apply audio effect (bass, nightcore)
- `!ping` — health check and branding message

Notes
- This scaffold downloads audio using `yt-dlp` into `/tmp` and streams it to the voice chat. For production use, add better queue management, error handling, caching, and resource cleanup.
