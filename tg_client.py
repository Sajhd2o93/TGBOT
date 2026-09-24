import os
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from config import BOT_TOKEN, API_ID, API_HASH, CHANNEL_ID

# Initialize Pyrogram Bot Client
tg_app = Client(
    "tg_cloud_bot",
    api_id=API_ID if API_ID else 12345,
    api_hash=API_HASH if API_HASH else "placeholder_hash",
    bot_token=BOT_TOKEN if BOT_TOKEN else "placeholder_token",
    workdir="."
)

_is_started = False
STORAGE_CHAT_ID = None

async def start_tg_client():
    global _is_started, STORAGE_CHAT_ID
    if _is_started and tg_app.is_connected:
        return True

    if not BOT_TOKEN or not API_ID or not API_HASH or API_ID == 0:
        print("⚠️ WARNING: BOT_TOKEN, API_ID, or API_HASH is missing in Environment Variables!")
        return False
    try:
        await tg_app.start()
        _is_started = True
        me = await tg_app.get_me()
        print(f"✅ Telegram Bot @{me.username} (ID: {me.id}) connected successfully!")
        
        # Resolve target channel to its persistent integer ID
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
    global _is_started
    try:
        if tg_app.is_connected:
            await tg_app.stop()
            _is_started = False
    except Exception as e:
        print(f"Error stopping Telegram client: {e}")

async def upload_to_channel(file_path: str, filename: str):
    """Uploads a file to the Telegram storage channel and returns the message_id."""
    global STORAGE_CHAT_ID
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected yet.")

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    abs_path = os.path.abspath(file_path)
    file_size = os.path.getsize(abs_path)
    
    print(f"📤 Starting MTProto upload for '{filename}' ({file_size} bytes) -> Chat ID: {target_chat}...")

    def progress_callback(current, total):
        pct = int(current * 100 / total) if total > 0 else 0
        if pct % 25 == 0 or current == total:
            print(f"   ⏳ Telegram upload '{filename}': {pct}% ({current}/{total} bytes)")

    try:
        msg = await tg_app.send_document(
            chat_id=target_chat,
            document=abs_path,
            file_name=filename,
            caption=f"📁 File: `{filename}`",
            progress=progress_callback
        )
        print(f"✅ Upload complete! Message ID: {msg.id} in chat {target_chat}")
        return msg.id
    except Exception as e:
        print(f"❌ Telegram send_document failed: {type(e).__name__} - {e}")
        raise ValueError(f"Telegram error: {type(e).__name__} - {str(e)}")

async def stream_file_from_channel(message_id: int):
    """Yields chunks of the file stored in Telegram channel message."""
    global STORAGE_CHAT_ID
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected.")

    target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
    msg = await tg_app.get_messages(target_chat, message_id)
    if not msg or not (msg.document or msg.video or msg.audio or msg.photo):
        raise ValueError("File not found in Telegram storage channel.")

    async for chunk in tg_app.stream_media(msg):
        yield chunk

async def delete_from_channel(message_id: int):
    """Deletes the file message from Telegram channel."""
    global STORAGE_CHAT_ID
    if not tg_app.is_connected:
        return
    try:
        target_chat = STORAGE_CHAT_ID if STORAGE_CHAT_ID is not None else CHANNEL_ID
        await tg_app.delete_messages(target_chat, message_id)
        print(f"🗑️ Deleted message {message_id} from Telegram channel.")
    except Exception as e:
        print(f"Error deleting message {message_id} from Telegram: {e}")
