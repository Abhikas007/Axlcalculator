import asyncio
import os
import subprocess
import tempfile
import uuid
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

# --- VERSION 3 SETUP ---
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream
    VOICE_CHAT_ENABLED = True
except ImportError as e:
    print(f"Note: pytgcalls not available - voice chat disabled: {e}")
    PyTgCalls = None
    MediaStream = None
    VOICE_CHAT_ENABLED = False

from .config import API_ID, API_HASH, BOT_TOKEN, PREFIX, DEFAULT_VOLUME

# Use SESSION_STRING for a user account (required to join voice chats).
SESSION_STRING = os.getenv("SESSION_STRING")

QUEUE: Dict[int, List[Dict]] = {}
LOOP: Dict[int, str] = {}

def make_client():
    if SESSION_STRING:
        return Client("axl_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
    if BOT_TOKEN:
        return Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    raise RuntimeError("Provide SESSION_STRING or BOT_TOKEN.")

app = make_client()
pytg = PyTgCalls(app) if VOICE_CHAT_ENABLED else None

def download_audio(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/axl_%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "cookiefile": "cookies.txt"
    }
    if not (query.startswith("http") or query.startswith("https")):
        query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info: info = info["entries"][0]
        filename = ydl.prepare_filename(info)
    return filename, info.get("title", "Unknown"), int(info.get("duration") or 0)

async def player_loop(chat_id: int):
    try:
        if not VOICE_CHAT_ENABLED: return
        while QUEUE.get(chat_id):
            item = QUEUE[chat_id][0]
            try:
                # VERSION 3 PLAY COMMAND
                stream = MediaStream(item["path"])
                await pytg.play(chat_id, stream)
            except Exception as e:
                print(f"Failed to play: {e}")
                break
            await asyncio.sleep(item.get("duration", 5))
            if LOOP.get(chat_id) == "one": continue
            elif LOOP.get(chat_id) == "all": QUEUE[chat_id].append(QUEUE[chat_id].pop(0))
            else: QUEUE[chat_id].pop(0)
        try:
            await pytg.leave_call(chat_id)
        except: pass
        QUEUE.pop(chat_id, None)
    except Exception as e:
        print(f"Loop error: {e}")

async def ensure_player(chat_id: int):
    if chat_id in QUEUE and QUEUE[chat_id]:
        asyncio.create_task(player_loop(chat_id))

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if len(message.command) < 2: return await message.reply_text("Usage: !play <song>")
    query = " ".join(message.command[1:])
    m = await message.reply_text("🔎 Searching...")
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, query)
    except Exception as e: return await m.edit_text(f"Error: {e}")
    
    chat_id = message.chat.id
    if chat_id not in QUEUE: QUEUE[chat_id] = []
    QUEUE[chat_id].append({"path": path, "title": title, "duration": duration})
    await m.delete()
    await message.reply_text(f"▶️ Added to Queue: **{title}**")
    await ensure_player(chat_id)

@app.on_message(filters.command("stop", PREFIX))
async def cmd_stop(_, message: Message):
    QUEUE.pop(message.chat.id, None)
    if VOICE_CHAT_ENABLED:
        try: await pytg.leave_call(message.chat.id)
        except: pass
    await message.reply_text("⏹ Stopped.")

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("AXL BOT is Alive! ⚡️")

async def main():
    await app.start()
    if VOICE_CHAT_ENABLED: await pytg.start()
    print("AXL MUSIC BOT STARTED ✅")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
