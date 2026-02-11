import asyncio
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp

from .config import API_ID, API_HASH, BOT_TOKEN, PREFIX

QUEUE = {}  # chat_id -> list of dicts {path,title,duration}

app = Client("axl_music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
pytg = PyTgCalls(app)


def download_audio(query: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "/tmp/axl_%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=True)
        filename = ydl.prepare_filename(info)
    title = info.get("title", "Unknown")
    duration = int(info.get("duration") or 0)
    return filename, title, duration


def apply_effect(src_path: str, preset: str) -> str:
    # Simple effect presets using ffmpeg audio filters
    tmp = tempfile.NamedTemporaryFile(prefix="axl_fx_", suffix=".mp3", delete=False)
    dst = tmp.name
    if preset == "bass":
        filt = "bass=g=10"
    elif preset == "nightcore":
        filt = "asetrate=44100*1.25,aresample=44100"
    else:
        filt = ""

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,
    ]
    if filt:
        cmd += ["-af", filt]
    cmd += [dst]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst


async def start_player(chat_id: int):
    queue = QUEUE.get(chat_id, [])
    while queue:
        item = queue[0]
        path = item["path"]
        await pytg.join_group_call(chat_id, AudioPiped(path))
        # wait for duration (fallback to 5s if unknown)
        await asyncio.sleep(max(5, item.get("duration", 5)))
        try:
            await pytg.leave_group_call(chat_id)
        except Exception:
            pass
        queue.pop(0)
    QUEUE.pop(chat_id, None)


@app.on_message(filters.command("join", PREFIX) & (filters.group | filters.channel))
async def cmd_join(_, message):
    await message.reply_text("AXL MUSIC BOT — joining voice chat when playback starts.")


@app.on_message(filters.command("leave", PREFIX) & (filters.group | filters.channel))
async def cmd_leave(_, message):
    chat_id = message.chat.id
    try:
        await pytg.leave_group_call(chat_id)
    except Exception:
        pass
    QUEUE.pop(chat_id, None)
    await message.reply_text("Left voice chat and cleared queue.")


@app.on_message(filters.command("play", PREFIX) & (filters.group | filters.channel))
async def cmd_play(_, message):
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
    QUEUE[chat_id].append({"path": path, "title": title, "duration": duration})
    await m.edit_text(f"Queued: {title} — duration: {duration}s")
    # if this is the only item, start player
    if len(QUEUE[chat_id]) == 1:
        asyncio.create_task(start_player(chat_id))


@app.on_message(filters.command("effects", PREFIX) & (filters.group | filters.channel))
async def cmd_effects(_, message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply_text("Usage: !effects <preset>. Presets: bass, nightcore")
    preset = message.command[1].lower()
    queue = QUEUE.get(chat_id)
    if not queue:
        return await message.reply_text("Queue is empty — play something first.")
    # apply effect to current/next track
    current = queue[0]
    src = current["path"]
    m = await message.reply_text(f"Applying effect: {preset} — this may take a few seconds")
    try:
        dst = await asyncio.get_running_loop().run_in_executor(None, apply_effect, src, preset)
    except Exception as e:
        return await m.edit_text(f"Effect failed: {e}")
    # replace path and restart playback for this chat
    current["path"] = dst
    await m.edit_text(f"Effect applied: {preset}")


@app.on_message(filters.command("ping", PREFIX))
async def cmd_ping(_, message):
    await message.reply_text("AXL MUSIC BOT — alive! Created by - @figletaxl Dev - Figletaxl")


async def main():
    await app.start()
    await pytg.start()
    print("AXL MUSIC BOT running")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
