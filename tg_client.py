import os
import asyncio
import zipfile
import io
from pyrogram import Client
from pyrogram.errors import FloodWait
from config import BOT_TOKEN, API_ID, API_HASH, CHANNEL_ID
from bot import register_bot_handlers

tg_app = None
STORAGE_CHAT_ID = None
max_known_id = 100

def get_file_category(filename: str, mime_type: str = "") -> str:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico", "avif"]:
        return "images"
    if ext in ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v"]:
        return "videos"
    if ext in ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"]:
        return "archives"
    if ext in ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "csv", "json", "xml", "log"]:
        return "documents"
    if ext in ["mp3", "wav", "ogg", "flac", "aac", "m4a", "opus"]:
        return "audio"
    return "other"

async def start_tg_client():
    global tg_app, STORAGE_CHAT_ID

    if not BOT_TOKEN or not API_ID or not API_HASH or API_ID == 0:
        print("⚠️ WARNING: BOT_TOKEN, API_ID, or API_HASH is missing in Environment Variables!")
        return False

    loop = asyncio.get_running_loop()
    
    tg_app = Client(
        "tg_cloud_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="."
    )
    tg_app.loop = loop

    try:
        await tg_app.start()
        register_bot_handlers(tg_app)
        
        me = await tg_app.get_me()
        print(f"✅ Telegram Bot @{me.username} (ID: {me.id}) connected successfully!")
        
        try:
            chat = await tg_app.get_chat(CHANNEL_ID)
            STORAGE_CHAT_ID = chat.id
            print(f"✅ Channel storage verified: '{chat.title}' (Resolved Integer ID: {STORAGE_CHAT_ID})")
        except Exception as e:
            print(f"⚠️ Warning resolving CHANNEL_ID ({CHANNEL_ID}): {e}")
            STORAGE_CHAT_ID = CHANNEL_ID
        
        return True
    except FloodWait as e:
        print(f"⌛ Telegram FLOOD_WAIT: need to wait {e.value} seconds (~{int(e.value//60)} mins) before authorizing bot token.")
        return False
    except Exception as e:
        print(f"❌ Error starting Telegram client: {type(e).__name__} - {e}")
        return False

async def stop_tg_client():
    global tg_app
    try:
        if tg_app and tg_app.is_connected:
            await tg_app.stop()
    except Exception as e:
        print(f"Error stopping Telegram client: {e}")

async def upload_to_channel(file_path: str, filename: str):
    """Uploads a file to the Telegram storage channel and returns the message_id."""
    global tg_app, STORAGE_CHAT_ID, max_known_id
    if not tg_app or not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected yet.")

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    abs_path = os.path.abspath(file_path)
    file_size = os.path.getsize(abs_path)
    
    print(f"📤 Uploading '{filename}' ({file_size} bytes) -> Chat ID: {target_chat}...")

    def progress_callback(current, total):
        pct = int(current * 100 / total) if total > 0 else 0
        if pct % 25 == 0 or current == total:
            print(f"   ⏳ Telegram upload '{filename}': {pct}% ({current}/{total} bytes)")

    try:
        msg = await tg_app.send_document(
            chat_id=target_chat,
            document=abs_path,
            file_name=filename,
            caption=f"📁 `{filename}`",
            progress=progress_callback
        )
        print(f"✅ Upload complete! Message ID: {msg.id}")
        if msg.id > max_known_id:
            max_known_id = msg.id
        return msg.id
    except Exception as e:
        print(f"❌ Telegram send_document failed: {type(e).__name__} - {e}")
        raise ValueError(f"Telegram error: {type(e).__name__} - {str(e)}")

async def get_channel_files(search_query: str = None):
    """Fetches all stored files from the Telegram channel using get_messages by ID range."""
    global tg_app, STORAGE_CHAT_ID, max_known_id
    if not tg_app or not tg_app.is_connected:
        return []

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    files = []

    try:
        upper_bound = max(max_known_id + 50, 200)
        id_list = list(range(1, upper_bound))

        for i in range(0, len(id_list), 200):
            batch = id_list[i:i + 200]
            msgs = await tg_app.get_messages(target_chat, batch)
            if not isinstance(msgs, list):
                msgs = [msgs]

            for msg in msgs:
                if not msg:
                    continue
                
                media = msg.document or msg.video or msg.audio or msg.photo
                if not media:
                    continue

                if msg.id > max_known_id:
                    max_known_id = msg.id

                if msg.document and msg.document.file_name:
                    filename = msg.document.file_name
                    file_size = msg.document.file_size
                    mime_type = msg.document.mime_type
                elif msg.video:
                    filename = getattr(msg.video, "file_name", f"video_{msg.id}.mp4")
                    file_size = msg.video.file_size
                    mime_type = getattr(msg.video, "mime_type", "video/mp4")
                elif msg.audio:
                    filename = getattr(msg.audio, "file_name", f"audio_{msg.id}.mp3")
                    file_size = msg.audio.file_size
                    mime_type = getattr(msg.audio, "mime_type", "audio/mpeg")
                elif msg.photo:
                    filename = f"photo_{msg.id}.jpg"
                    file_size = getattr(msg.photo, "file_size", 0)
                    mime_type = "image/jpeg"
                else:
                    filename = f"file_{msg.id}"
                    file_size = getattr(media, "file_size", 0)
                    mime_type = getattr(media, "mime_type", "application/octet-stream")

                if search_query and search_query.lower() not in filename.lower():
                    continue

                created_at = msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else ""
                category = get_file_category(filename, mime_type)

                files.append({
                    "id": msg.id,
                    "filename": filename,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "category": category,
                    "message_id": msg.id,
                    "created_at": created_at
                })

        files.sort(key=lambda x: x["id"], reverse=True)

    except Exception as e:
        print(f"Error fetching channel files via get_messages: {e}")

    return files

async def stream_file_from_channel(message_id: int):
    """Yields chunks of the file stored in Telegram channel message."""
    global tg_app, STORAGE_CHAT_ID
    if not tg_app or not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected.")

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    msg = await tg_app.get_messages(target_chat, message_id)
    if not msg or not (msg.document or msg.video or msg.audio or msg.photo):
        raise ValueError("File not found in Telegram storage channel.")

    async for chunk in tg_app.stream_media(msg):
        yield chunk

async def delete_from_channel(message_id: int):
    """Deletes the file message from Telegram channel."""
    global tg_app, STORAGE_CHAT_ID
    if not tg_app or not tg_app.is_connected:
        return
    try:
        target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
        await tg_app.delete_messages(target_chat, message_id)
        print(f"🗑️ Deleted message {message_id} from Telegram channel.")
    except Exception as e:
        print(f"Error deleting message {message_id} from Telegram: {e}")
