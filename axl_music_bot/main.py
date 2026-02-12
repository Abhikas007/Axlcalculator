import asyncio
import os
import subprocess
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

# --- ENV VARS ---
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
DEFAULT_VOLUME = int(os.getenv("DEFAULT_VOLUME", "100"))

# --- PREFIX SETUP ---
PREFIX = ["!", ".", "/"]

# --- PYTGCALLS V2 SETUP (STABLE) ---
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioPiped  # V2 Import
    VOICE_CHAT_ENABLED = True
except ImportError:
    try:
        # Fallback for some v2 sub-versions
        from pytgcalls.types.input_stream import AudioPiped
        VOICE_CHAT_ENABLED = True
    except ImportError as e:
        print(f"⚠️ Error: pytgcalls import failed: {e}")
        PyTgCalls = None
        AudioPiped = None
        VOICE_CHAT_ENABLED = False

QUEUE: Dict[int, List[Dict]] = {}
LOOP: Dict[int, str] = {}

def make_client():
    if SESSION_STRING:
        print("✅ Using Session String for Userbot")
        return Client("axl_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
    if BOT_TOKEN:
        print("⚠️ Using Bot Token")
        return Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    raise RuntimeError("❌ Error: SESSION_STRING or BOT_TOKEN missing")

app = make_client()
pytg = PyTgCalls(app) if VOICE_CHAT_ENABLED else None

def download_audio(query: str):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "/tmp/axl_%(id)s.%(ext)s", "quiet": True, "noplaylist": True}
    if os.path.exists("cookies.txt"): ydl_opts["cookiefile"] = "cookies.txt"
    if not (query.startswith("http") or query.startswith("https")): query = f"ytsearch1:{query}"
    
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
                # --- V2 PLAY LOGIC (STABLE) ---
                stream = AudioPiped(item["path"])
                await pytg.join_group_call(chat_id, stream)
            except Exception as e:
                print(f"❌ Play Error: {e}")
                break
            
            await asyncio.sleep(item.get("duration", 5))
            
            if LOOP.get(chat_id) == "one": continue
            elif LOOP.get(chat_id) == "all": QUEUE[chat_id].append(QUEUE[chat_id].pop(0))
            else: QUEUE[chat_id].pop(0)
        
        try: await pytg.leave_group_call(chat_id)
        except: pass
        QUEUE.pop(chat_id, None)
    except Exception as e:
        print(f"Loop Error: {e}")

async def ensure_player(chat_id: int):
    if chat_id in QUEUE and QUEUE[chat_id] and len(QUEUE[chat_id]) == 1:
        asyncio.create_task(player_loop(chat_id))

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
    await ensure_player(chat_id)

@app.on_message(filters.command("stop", PREFIX))
async def cmd_stop(_, message: Message):
    QUEUE.pop(message.chat.id, None)
    if VOICE_CHAT_ENABLED:
        try: await pytg.leave_group_call(message.chat.id)
        except: pass
    await message.reply_text("⏹ **Stopped.**")

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive!**")

async def main():
    print("🔄 Starting Client...")
    await app.start()
    
    # Peer ID Crash Fix
    print("🔄 Refreshing Dialogs...")
    try:
        async for dialog in app.get_dialogs(limit=50): pass
    except: pass
    
    if VOICE_CHAT_ENABLED:
        print("🔄 Starting PyTgCalls V2...")
        await pytg.start()
        print("✅ PyTgCalls Started!")
    
    print("🚀 AXL MUSIC BOT RUNNING...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
