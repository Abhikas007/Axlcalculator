import asyncio
import os
from typing import Dict, List
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

# --- STRICT V2 SETUP ---
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types.input_stream import AudioPiped
    VOICE_CHAT_ENABLED = True
except ImportError as e:
    print(f"⚠️ Error: pytgcalls V2 import failed: {e}")
    VOICE_CHAT_ENABLED = False

# ENV VARS
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
PREFIX = ["!", ".", "/"]

QUEUE: Dict[int, List[Dict]] = {}

def make_client():
    if SESSION_STRING:
        return Client("axl_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
    return Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

app = make_client()
pytg = PyTgCalls(app) if VOICE_CHAT_ENABLED else None

def download_audio(query: str):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "/tmp/axl_%(id)s.%(ext)s", "quiet": True, "noplaylist": True}
    if not (query.startswith("http") or query.startswith("https")): query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info: info = info["entries"][0]
        filename = ydl.prepare_filename(info)
    return filename, info.get("title", "Unknown"), int(info.get("duration") or 0)

async def player_loop(chat_id: int):
    try:
        while QUEUE.get(chat_id):
            item = QUEUE[chat_id][0]
            try:
                # V2 Playing Method
                await pytg.join_group_call(chat_id, AudioPiped(item["path"]))
            except Exception as e:
                print(f"❌ Play Error: {e}")
                break
            await asyncio.sleep(item.get("duration", 5))
            QUEUE[chat_id].pop(0)
        try: await pytg.leave_group_call(chat_id)
        except: pass
        QUEUE.pop(chat_id, None)
    except Exception as e: print(f"Loop Error: {e}")

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if len(message.command) < 2: return await message.reply_text("ℹ️ Usage: `!play Song Name`")
    m = await message.reply_text("🔎 **Searching...**")
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, " ".join(message.command[1:]))
    except Exception as e: return await m.edit_text(f"❌ Error: {e}")
    
    chat_id = message.chat.id
    if chat_id not in QUEUE: QUEUE[chat_id] = []
    QUEUE[chat_id].append({"path": path, "title": title, "duration": duration})
    await m.delete()
    await message.reply_text(f"🎵 **Queued:** {title}")
    if len(QUEUE[chat_id]) == 1: asyncio.create_task(player_loop(chat_id))

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive (Baryon Mode)!**")

async def main():
    await app.start()
    print("🔄 Refreshing Dialogs...")
    try:
        async for dialog in app.get_dialogs(limit=20): pass
    except: pass
    if VOICE_CHAT_ENABLED: await pytg.start()
    print("🚀 AXL MUSIC BOT RUNNING (V2 STABLE)...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
