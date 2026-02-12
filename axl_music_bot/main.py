import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped

# ENV VARS
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
PREFIX = ["!", ".", "/"]

app = Client("axl_music", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING) if SESSION_STRING else Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytg = PyTgCalls(app)

def download_audio(query: str):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "/tmp/axl_%(id)s.%(ext)s", "quiet": True, "noplaylist": True}
    if not (query.startswith("http") or query.startswith("https")): query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        if "entries" in info: info = info["entries"][0]
        return ydl.prepare_filename(info), info.get("title", "Unknown"), int(info.get("duration") or 0)

async def player(chat_id: int, path: str):
    try:
        await pytg.join_group_call(chat_id, AudioPiped(path))
    except Exception as e:
        print(f"Play Error: {e}")

@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    if len(message.command) < 2: return await message.reply_text("ℹ️ Usage: `!play Song Name`")
    m = await message.reply_text("🔎 **Searching...**")
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, " ".join(message.command[1:]))
        await m.edit_text(f"🎵 **Playing:** {title}")
        await player(message.chat.id, path)
    except Exception as e: await m.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("⚡️ **AXL MUSIC BOT is Alive (Final Baryon)!**")

async def main():
    await app.start()
    await pytg.start()
    print("🚀 AXL MUSIC BOT RUNNING!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
