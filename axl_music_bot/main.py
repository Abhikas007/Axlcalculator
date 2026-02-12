import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp

# --- ULTRA STABLE IMPORT BLOCK ---
try:
    from pytgcalls import PyTgCalls
    try:
        # Version 2 Style
        from pytgcalls.types import AudioPiped as StreamType
    except ImportError:
        try:
            from pytgcalls.types.input_stream import AudioPiped as StreamType
        except ImportError:
            # Version 3 Style
            from pytgcalls.types import MediaStream as StreamType
    print("✅ Pytgcalls Library Loaded!")
except ImportError:
    print("❌ All Pytgcalls imports failed!")
    StreamType = None

# ENV VARS
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
PREFIX = ["!", ".", "/"]

# Initialize Client
app = Client(
    "axl_music", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=SESSION_STRING if SESSION_STRING else None,
    bot_token=BOT_TOKEN if not SESSION_STRING else None
)

pytg = PyTgCalls(app) if StreamType else None

def download_audio(query: str):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "/tmp/axl_%(id)s.%(ext)s", "quiet": True, "noplaylist": True}
    if not (query.startswith("http") or query.startswith("https")): query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info: info = info["entries"][0]
        return ydl.prepare_filename(info), info.get("title", "Unknown"), int(info.get("duration") or 0)

async def player(chat_id: int, path: str):
    try:
        if hasattr(pytg, 'join_group_call'):
            await pytg.join_group_call(chat_id, StreamType(path))
        else:
            await pytg.play(chat_id, StreamType(path))
    except Exception as e:
        print(f"❌ Play Error: {e}")

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if not StreamType: return await message.reply_text("❌ Library Error!")
    if len(message.command) < 2: return await message.reply_text("ℹ️ Usage: `!play Song Name`")
    m = await message.reply_text("🔎 **Searching...**")
    try:
        # Peer resolve karne ki koshish (Auto-learning)
        try:
            await app.get_chat(message.chat.id)
        except:
            pass
            
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, " ".join(message.command[1:]))
        await m.edit_text(f"🎵 **Playing:** {title}")
        await player(message.chat.id, path)
    except Exception as e: 
        await m.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive & IDs are Fixed!**")

async def main():
    print("🔄 Starting Client...")
    await app.start()
    
    # --- SAGE PERCEPTION: Refresh Dialogs to fix Peer ID Invalid ---
    print("🔄 Refreshing all Dialogs (Learning Peer IDs)...")
    try:
        async for dialog in app.get_dialogs(limit=30):
            pass # Bot chats ko dekh raha hai taaki IDs yaad ho jayein
        print("✅ Dialogs Refreshed!")
    except Exception as e:
        print(f"⚠️ Dialog Refresh Warning: {e}")

    if pytg: 
        await pytg.start()
        print("✅ Pytgcalls Started!")
        
    print("🚀 AXL MUSIC BOT RUNNING!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
