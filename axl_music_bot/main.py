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

# --- UNIVERSAL PYTGCALLS SETUP (V2 & V3 SUPPORT) ---
IS_V3 = False
try:
    from pytgcalls import PyTgCalls
    try:
        # Koshish karo V3 (New) dhoondne ki
        from pytgcalls.types import MediaStream
        IS_V3 = True
        print("✅ Detected PyTgCalls Version 3 (MediaStream)")
    except ImportError:
        # Agar nahi mila, toh V2 (Old) try karo
        try:
            from pytgcalls.types import AudioPiped
            MediaStream = AudioPiped # Alias bana diya taaki code na phate
            IS_V3 = False
            print("✅ Detected PyTgCalls Version 2 (AudioPiped)")
        except ImportError:
            # Fallback for older V2 versions
            from pytgcalls.types.input_stream import AudioPiped
            MediaStream = AudioPiped
            IS_V3 = False
            print("✅ Detected PyTgCalls Version 2 (Input Stream)")
            
    VOICE_CHAT_ENABLED = True
except ImportError as e:
    print(f"⚠️ Error: pytgcalls import failed: {e}")
    PyTgCalls = None
    MediaStream = None
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
                stream = MediaStream(item["path"])
                
                # --- AUTO DETECT PLAY METHOD ---
                if IS_V3:
                    await pytg.play(chat_id, stream) # V3 Style
                else:
                    await pytg.join_group_call(chat_id, stream) # V2 Style
                # -------------------------------
                
            except Exception as e:
                print(f"❌ Play Error: {e}")
                break
            
            await asyncio.sleep(item.get("duration", 5))
            
            if LOOP.get(chat_id) == "one": continue
            elif LOOP.get(chat_id) == "all": QUEUE[chat_id].append(QUEUE[chat_id].pop(0))
            else: QUEUE[chat_id].pop(0)
        
        try: 
            if IS_V3: await pytg.leave_call(chat_id)
            else: await pytg.leave_group_call(chat_id)
        except: pass
        QUEUE.pop(chat_id, None)
    except Exception as e:
        print(f"Loop Error: {e}")

async def ensure_player(chat_id: int):
    if chat_id in QUEUE and QUEUE[chat_id]:
        if len(QUEUE[chat_id]) == 1:
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
        try: 
            if IS_V3: await pytg.leave_call(message.chat.id)
            else: await pytg.leave_group_call(message.chat.id)
        except: pass
    await message.reply_text("⏹ **Stopped.**")

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive!**")

async def main():
    print("🔄 Starting Client...")
    await app.start()
    
    print("🔄 Refreshing Dialogs...")
    try:
        async for dialog in app.get_dialogs(limit=50): pass
    except: pass
    
    if VOICE_CHAT_ENABLED:
        print("🔄 Starting PyTgCalls...")
        await pytg.start()
        print("✅ PyTgCalls Started!")
    else:
        print("❌ Voice Chat Disabled")
    
    print("🚀 AXL MUSIC BOT RUNNING...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
