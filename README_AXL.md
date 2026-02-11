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

Session strings and voice chats
- Telegram bots (the ones created via @BotFather and using a `BOT_TOKEN`) cannot join voice chats. To stream into voice chats you must run the bot as a user account (a "userbot") using a session string.

Generate a Pyrogram session string (recommended):

1. Install dependencies locally:

```bash
python -m pip install pyrogram tgcrypto
```

2. Run a quick script to get a session string (run locally on your machine, not on shared servers):

```python
from pyrogram import Client
API_ID = int(input('API_ID: '))
API_HASH = input('API_HASH: ')
with Client('gen', api_id=API_ID, api_hash=API_HASH) as app:
	print('Session string:', app.export_session_string())
```

Use that `SESSION_STRING` in the Koyeb environment variables to allow the container to act as a user and join voice chats.

Deploying to Koyeb (step-by-step)

1. Push this repository to GitHub (already done).
2. In Koyeb, create a new app and choose "Deploy from Git".
3. Point Koyeb to your GitHub repo and branch `main` and use the included `Dockerfile`.
4. In Koyeb's Environment variables, set:

- `API_ID` — your Telegram API ID
- `API_HASH` — your Telegram API hash
- `SESSION_STRING` — session string generated earlier (required for voice)
- `PREFIX` — `!` (default)
- `DEFAULT_VOLUME` — `100`

5. Start the service. Monitor logs for successful startup.

Notes on hosting choice
- Koyeb works well for containers and provides a free trial. For voice streaming you need a stable connection and a long-running container. Avoid serverless functions.
- Alternatives: a small VPS (Hetzner, DigitalOcean), Render, or Railway. For simple deployment Koyeb is fine during your 6-day trial.

Security and best-practices
- Keep your `SESSION_STRING`, `API_HASH`, and `API_ID` private.
- Use a user account created specifically for this purpose, not your personal account.
- Monitor CPU/memory usage: audio transcoding uses CPU (ffmpeg).

Useful commands

```bash
# Build locally
docker build -t axl-music-bot .

# Run with env file locally
docker run --env-file .env -it axl-music-bot
```

If you want, I can:
- Add pause/resume, skip confirmation, better cleanup, and persistent caching.
- Create a PR instead of pushing to `main`.
