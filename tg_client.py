import os
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from config import BOT_TOKEN, API_ID, API_HASH, CHANNEL_ID

# Initialize Pyrogram Bot Client with session file persistence
tg_app = Client(
    "tg_cloud_bot",
    api_id=API_ID if API_ID else 12345,
    api_hash=API_HASH if API_HASH else "placeholder_hash",
    bot_token=BOT_TOKEN if BOT_TOKEN else "placeholder_token",
    workdir="."
)

async def start_tg_client():
    if not BOT_TOKEN or not API_ID or not API_HASH or API_ID == 0:
        print("⚠️ WARNING: BOT_TOKEN, API_ID, or API_HASH is missing in Environment Variables!")
        return False
    try:
        await tg_app.start()
        print("✅ Telegram MTProto client started successfully!")
        return True
    except FloodWait as e:
        print(f"⌛ Telegram FLOOD_WAIT: Telegram requires a wait of {e.value} seconds (~{int(e.value//60)} mins) before authorizing this bot token again.")
        print("💡 The Web App UI is active. Telegram file uploads/downloads will resume after the wait time expires.")
        return False
    except Exception as e:
        print(f"❌ Error starting Telegram Pyrogram client: {e}")
        return False

async def stop_tg_client():
    try:
        if tg_app.is_connected:
            await tg_app.stop()
    except Exception as e:
        print(f"Error stopping Telegram client: {e}")

async def upload_to_channel(file_path: str, filename: str, progress_callback=None):
    """Uploads a file to the Telegram storage channel and returns the message_id."""
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected. Please check if Telegram FLOOD_WAIT timer is active or check credentials.")

    msg = await tg_app.send_document(
        chat_id=CHANNEL_ID,
        document=file_path,
        file_name=filename,
        caption=f"📁 File: `{filename}`",
        progress=progress_callback
    )
    return msg.id

async def stream_file_from_channel(message_id: int):
    """Yields chunks of the file stored in Telegram channel message."""
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected. Please check if Telegram FLOOD_WAIT timer is active or check credentials.")

    msg = await tg_app.get_messages(CHANNEL_ID, message_id)
    if not msg or not (msg.document or msg.video or msg.audio or msg.photo):
        raise ValueError("File not found in Telegram storage channel.")

    async for chunk in tg_app.stream_media(msg):
        yield chunk

async def delete_from_channel(message_id: int):
    """Deletes the file message from Telegram channel."""
    if not tg_app.is_connected:
        return
    try:
        await tg_app.delete_messages(CHANNEL_ID, message_id)
    except Exception as e:
        print(f"Error deleting message {message_id} from Telegram: {e}")
