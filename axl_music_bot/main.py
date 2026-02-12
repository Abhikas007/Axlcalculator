import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, PersistentTimestampInvalid
import yt_dlp

# --- STABLE IMPORT BLOCK ---
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import AudioPiped as StreamType
    print("✅ Pytgcalls V2 Loaded!")
except ImportError:
    from pytgcalls.types import MediaStream as StreamType
    print("✅ Pytgcalls V3 Loaded!")

# ENV VARS
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
PREFIX = ["!", ".", "/"]

# --- APP INITIALIZATION (Baryon Mode v2) ---
app = Client(
    "axl_music", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=SESSION_STRING if SESSION_STRING else None,
    bot_token=BOT_TOKEN if not SESSION_STRING else None,
    sleep_threshold=60  # Bot ko zyada sabar sikhana padega
)

pytg = PyTgCalls(app)

def download_audio(query: str):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "/tmp/axl_%(id)s.%(ext)s", "quiet": True, "noplaylist": True}
    if not (query.startswith("http") or query.startswith("https")): query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info: info = info["entries"][0]
        return ydl.prepare_filename(info), info.get("title", "Unknown"), int(info.get("duration") or 0)

# --- COMMAND HANDLERS ---

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive (Baryon v2 Success)!**")

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if len(message.command) < 2: 
        return await message.reply_text("ℹ️ Usage: `!play Song Name`")
    m = await message.reply_text("🔎 **Searching...**")
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, " ".join(message.command[1:]))
        await m.edit_text(f"🎵 **Playing:** {title}")
        if hasattr(pytg, 'join_group_call'):
            await pytg.join_group_call(message.chat.id, StreamType(path))
        else:
            await pytg.play(message.chat.id, StreamType(path))
    except Exception as e: await m.edit_text(f"❌ Error: {e}")

# --- STARTUP LOGIC ---
async def main():
    try:
        print("🔄 Starting Client...")
        await app.start()
        
        # Peer resolving fix
        print("🔄 Syncing with Telegram (Sage Perception)...")
        async for dialog in app.get_dialogs(limit=20):
            pass
            
        print("🔄 Starting Voice Engine...")
        await pytg.start()
        print("🚀 AXL MUSIC BOT RUNNING!")
        await asyncio.Event().wait()
    except PersistentTimestampInvalid:
        print("⚠️ Timestamp error caught! Restarting in 5 seconds...")
        await asyncio.sleep(5)
        await main() # Auto-restart logic
    except Exception as e:
        print(f"❌ Fatal Error: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
