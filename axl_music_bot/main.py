import asyncio
import os
import subprocess
import uuid
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

# --- ENV VARS SETUP (Directly from Koyeb) ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
DEFAULT_VOLUME = int(os.getenv("DEFAULT_VOLUME", "100"))

# --- PREFIX SETUP (Fixed for commands) ---
# Ab bot inn teeno symbols par chalega
PREFIX = ["!", ".", "/"]

# --- PYTGCALLS V3 SETUP ---
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream
    VOICE_CHAT_ENABLED = True
except ImportError as e:
    print(f"⚠️ Error: pytgcalls import failed: {e}")
    PyTgCalls = None
    MediaStream = None
    VOICE_CHAT_ENABLED = False

# QUEUE SYSTEM
QUEUE: Dict[int, List[Dict]] = {}
LOOP: Dict[int, str] = {}

def make_client():
    # Priority: Session String (User) > Bot Token
    if SESSION_STRING:
        print("✅ Using Session String for Userbot")
        return Client("axl_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
    if BOT_TOKEN:
        print("⚠️ Using Bot Token (Voice Chat might not work properly without User)")
        return Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    raise RuntimeError("❌ Error: SESSION_STRING or BOT_TOKEN missing in Koyeb Vars")

app = make_client()
pytg = PyTgCalls(app) if VOICE_CHAT_ENABLED else None

def download_audio(query: str):
    # Check if cookies file exists to avoid crashes
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/axl_%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    if os.path.exists("cookies.txt"):
        ydl_opts["cookiefile"] = "cookies.txt"
    
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
                # --- V3 PLAY LOGIC ---
                stream = MediaStream(item["path"])
                await pytg.play(chat_id, stream)
            except Exception as e:
                print(f"❌ Play Error: {e}")
                break
            
            # Wait for song to finish
            await asyncio.sleep(item.get("duration", 5))
            
            # Loop Logic
            if LOOP.get(chat_id) == "one": continue
            elif LOOP.get(chat_id) == "all": QUEUE[chat_id].append(QUEUE[chat_id].pop(0))
            else: QUEUE[chat_id].pop(0)
        
        # Leave call when queue empty
        try: await pytg.leave_call(chat_id)
        except: pass
        QUEUE.pop(chat_id, None)
    except Exception as e:
        print(f"Loop Error: {e}")

async def ensure_player(chat_id: int):
    if chat_id in QUEUE and QUEUE[chat_id]:
        # Avoid creating multiple tasks if already playing (simplified check)
        if len(QUEUE[chat_id]) == 1: 
            asyncio.create_task(player_loop(chat_id))

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if len(message.command) < 2: 
        return await message.reply_text("ℹ️ **Usage:** `!play Song Name`")
    
    query = " ".join(message.command[1:])
    m = await message.reply_text("🔎 **Searching...**")
    
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, query)
    except Exception as e: 
        return await m.edit_text(f"❌ **Error:** {e}")
    
    chat_id = message.chat.id
    if chat_id not in QUEUE: QUEUE[chat_id] = []
    
    QUEUE[chat_id].append({"path": path, "title": title, "duration": duration})
    await m.delete()
    await message.reply_text(f"🎵 **Added to Queue:** {title}\n⏱ **Duration:** {duration}s")
    
    await ensure_player(chat_id)

@app.on_message(filters.command("stop", PREFIX))
async def cmd_stop(_, message: Message):
    QUEUE.pop(message.chat.id, None)
    if VOICE_CHAT_ENABLED:
        try: await pytg.leave_call(message.chat.id)
        except: pass
    await message.reply_text("⏹ **Stopped and Cleared Queue.**")

@app.on_message(filters.command("ping", PREFIX) & ~filters.private)
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive!**")

async def main():
    print("🔄 Starting Client...")
    await app.start()
    print("✅ Client Started!")
    
    if VOICE_CHAT_ENABLED:
        print("🔄 Starting PyTgCalls...")
        await pytg.start()
        print("✅ PyTgCalls Started!")
    else:
        print("❌ Voice Chat Disabled (Missing Requirements)")
        
    print("🚀 AXL MUSIC BOT RUNNING...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
