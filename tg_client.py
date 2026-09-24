import os
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait
from config import BOT_TOKEN, API_ID, API_HASH, CHANNEL_ID
from bot import register_bot_handlers
from database import add_or_update_file

tg_app = None
STORAGE_CHAT_ID = None

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

async def sync_existing_channel_files():
    """Scans the channel in background to populate DB with any files already in Telegram."""
    global tg_app, STORAGE_CHAT_ID
    if not tg_app or not tg_app.is_connected:
        return

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    print(f"🔄 Scanning channel ({target_chat}) for existing files...")
    
    try:
        # Check first 50 message IDs
        ids_to_check = list(range(1, 50))
        msgs = await tg_app.get_messages(target_chat, ids_to_check)
        if not isinstance(msgs, list):
            msgs = [msgs]

        found_count = 0
        for msg in msgs:
            if not msg:
                continue
            media = msg.document or msg.video or msg.audio or msg.photo
            if not media:
                continue

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

            category = get_file_category(filename, mime_type)
            created_at = msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else None

            await add_or_update_file(
                message_id=msg.id,
                filename=filename,
                file_size=file_size,
                mime_type=mime_type,
                category=category,
                created_at=created_at
            )
            found_count += 1

        print(f"✅ Sync complete: found {found_count} files in channel.")
    except Exception as e:
        print(f"Sync warning: {e}")

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

        # Background sync without blocking server boot
        asyncio.create_task(sync_existing_channel_files())
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
    global tg_app, STORAGE_CHAT_ID
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
        return msg.id
    except Exception as e:
        print(f"❌ Telegram send_document failed: {type(e).__name__} - {e}")
        raise ValueError(f"Telegram error: {type(e).__name__} - {str(e)}")

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

async def download_file_to_temp(message_id: int, destination_path: str):
    """Downloads a media file from Telegram to a local temporary path."""
    global tg_app, STORAGE_CHAT_ID
    if not tg_app or not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected.")
    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    msg = await tg_app.get_messages(target_chat, message_id)
    if not msg:
        raise ValueError("File not found in Telegram.")
    
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    res = await tg_app.download_media(msg, file_name=destination_path)
    return res

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
