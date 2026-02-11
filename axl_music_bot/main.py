import asyncio
import os
import subprocess
import tempfile
import uuid
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

from .config import API_ID, API_HASH, BOT_TOKEN, PREFIX, DEFAULT_VOLUME

# Use SESSION_STRING for a user account (required to join voice chats).
SESSION_STRING = os.getenv("SESSION_STRING")

# QUEUE structure: chat_id -> list[ {id, path, title, duration, requester, volume} ]
QUEUE: Dict[int, List[Dict]] = {}
LOOP: Dict[int, str] = {}  # chat_id -> 'none'|'one'|'all'


def make_client():
    # If SESSION_STRING provided, create a user client (required to join voice chats).
    if SESSION_STRING:
        return Client("axl_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
    # Fall back to bot token for text-only commands (won't join voice chats).
    if BOT_TOKEN:
        return Client("axl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
    raise RuntimeError("Provide SESSION_STRING for user account or BOT_TOKEN for bot commands.")


app = make_client()
pytg = PyTgCalls(app)


def download_audio(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/axl_%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    # If not a URL, use ytsearch
    if not (query.startswith("http://") or query.startswith("https://")):
        query = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        # When using ytsearch, info is a playlist-like dict
        if "entries" in info:
            info = info["entries"][0]
        filename = ydl.prepare_filename(info)
    title = info.get("title", "Unknown")
    duration = int(info.get("duration") or 0)
    return filename, title, duration


def apply_effect(src_path: str, preset: str, volume: int = 100) -> str:
    tmp = tempfile.NamedTemporaryFile(prefix="axl_fx_", suffix=".mp3", delete=False)
    dst = tmp.name
    filters = []
    if preset == "bass":
        filters.append("bass=g=10")
    elif preset == "nightcore":
        filters.append("asetrate=44100*1.25,aresample=44100")
    elif preset == "vapor":
        filters.append("atempo=0.9,asetrate=44100*0.9,aresample=44100")
    elif preset == "slow":
        filters.append("atempo=0.8")

    # volume filter
    if volume and volume != 100:
        vol = float(volume) / 100.0
        filters.append(f"volume={vol}")

    cmd = ["ffmpeg", "-y", "-i", src_path]
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += [dst]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst


def generate_cover(title: str, requester: str) -> str:
    # Create a simple cover image with Pillow
    width, height = 1024, 512
    img = Image.new("RGB", (width, height), (18, 24, 39))
    draw = ImageDraw.Draw(img)
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        title_font = ImageFont.truetype(font_path, 40)
        small_font = ImageFont.truetype(font_path, 24)
    except Exception:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.text((40, 40), "AXL MUSIC BOT", fill=(255, 180, 0), font=title_font)
    draw.text((40, 120), title[:120], fill=(255, 255, 255), font=small_font)
    draw.text((40, 420), f"Requested by: {requester}", fill=(200, 200, 200), font=small_font)
    path = f"/tmp/axl_cover_{uuid.uuid4().hex}.png"
    img.save(path)
    return path


async def ensure_player(chat_id: int):
    if chat_id in QUEUE and QUEUE[chat_id]:
        # If not already playing, start
        asyncio.create_task(player_loop(chat_id))


async def player_loop(chat_id: int):
    try:
        while QUEUE.get(chat_id):
            item = QUEUE[chat_id][0]
            path = item["path"]
            try:
                await pytg.join_group_call(chat_id, AudioPiped(path))
            except Exception:
                # join failed, notify and break
                break
            duration = max(5, item.get("duration", 5))
            await asyncio.sleep(duration)
            # after playing
            if LOOP.get(chat_id) == "one":
                # keep same
                continue
            elif LOOP.get(chat_id) == "all":
                QUEUE[chat_id].append(QUEUE[chat_id].pop(0))
            else:
                QUEUE[chat_id].pop(0)
        try:
            await pytg.leave_group_call(chat_id)
        except Exception:
            pass
        QUEUE.pop(chat_id, None)
    except Exception:
        QUEUE.pop(chat_id, None)


def format_queue(chat_id: int) -> str:
    q = QUEUE.get(chat_id, [])
    if not q:
        return "Queue is empty."
    s = []
    for i, item in enumerate(q[:10], 1):
        s.append(f"{i}. {item.get('title','Unknown')} — {item.get('duration',0)}s")
    return "\n".join(s)


@app.on_message(filters.command("play", PREFIX))
async def cmd_play(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply_text("Usage: !play <url or search term>")
    query = " ".join(message.command[1:])
    m = await message.reply_text(f"🔎 Searching: {query}")
    try:
        path, title, duration = await asyncio.get_running_loop().run_in_executor(None, download_audio, query)
    except Exception as e:
        return await m.edit_text(f"Failed to download: {e}")

    if chat_id not in QUEUE:
        QUEUE[chat_id] = []
    track = {"id": uuid.uuid4().hex, "path": path, "title": title, "duration": duration, "requester": message.from_user.first_name if message.from_user else "unknown", "volume": DEFAULT_VOLUME}
    QUEUE[chat_id].append(track)
    cover = generate_cover(title, track["requester"])
    await m.delete()
    await message.reply_photo(cover, caption=f"Queued: {title} — {duration}s")
    await ensure_player(chat_id)


@app.on_message(filters.command("queue", PREFIX))
async def cmd_queue(_, message: Message):
    await message.reply_text(format_queue(message.chat.id))


@app.on_message(filters.command("skip", PREFIX))
async def cmd_skip(_, message: Message):
    chat_id = message.chat.id
    q = QUEUE.get(chat_id)
    if not q:
        return await message.reply_text("Queue empty.")
    q.pop(0)
    await message.reply_text("Skipped.")


@app.on_message(filters.command("stop", PREFIX))
async def cmd_stop(_, message: Message):
    chat_id = message.chat.id
    QUEUE.pop(chat_id, None)
    try:
        await pytg.leave_group_call(chat_id)
    except Exception:
        pass
    await message.reply_text("Stopped and cleared queue.")


@app.on_message(filters.command("effects", PREFIX))
async def cmd_effects(_, message: Message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply_text("Usage: !effects <preset> [volume]. Presets: bass, nightcore, vapor, slow")
    preset = message.command[1].lower()
    vol = DEFAULT_VOLUME
    if len(message.command) >= 3:
        try:
            vol = int(message.command[2])
        except Exception:
            pass
    q = QUEUE.get(chat_id)
    if not q:
        return await message.reply_text("Queue empty — play first.")
    current = q[0]
    await message.reply_text(f"Applying {preset} (volume={vol}) — processing...")
    try:
        dst = await asyncio.get_running_loop().run_in_executor(None, apply_effect, current["path"], preset, vol)
    except Exception as e:
        return await message.reply_text(f"Effect failed: {e}")
    current["path"] = dst
    current["volume"] = vol
    await message.reply_text("Effect applied.")


@app.on_message(filters.command("loop", PREFIX))
async def cmd_loop(_, message: Message):
    chat_id = message.chat.id
    mode = (message.command[1].lower() if len(message.command) > 1 else "none")
    if mode not in ("none", "one", "all"):
        return await message.reply_text("Loop modes: none, one, all")
    LOOP[chat_id] = mode
    await message.reply_text(f"Loop set: {mode}")


@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message: Message):
    await message.reply_text("AXL MUSIC BOT — alive! Created by - @figletaxl Dev - Figletaxl")


async def main():
    await app.start()
    await pytg.start()
    print("AXL MUSIC BOT running")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
