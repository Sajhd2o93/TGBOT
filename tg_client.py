import os
import asyncio
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH, CHANNEL_ID

# Initialize Pyrogram Bot Client
tg_app = Client(
    "tg_cloud_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

async def start_tg_client():
    await tg_app.start()

async def stop_tg_client():
    await tg_app.stop()

async def upload_to_channel(file_path: str, filename: str, progress_callback=None):
    """Uploads a file to the Telegram storage channel and returns the message_id."""
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
    msg = await tg_app.get_messages(CHANNEL_ID, message_id)
    if not msg or not (msg.document or msg.video or msg.audio or msg.photo):
        raise ValueError("File not found in Telegram storage channel.")

    async for chunk in tg_app.stream_media(msg):
        yield chunk

async def delete_from_channel(message_id: int):
    """Deletes the file message from Telegram channel."""
    try:
        await tg_app.delete_messages(CHANNEL_ID, message_id)
    except Exception as e:
        print(f"Error deleting message {message_id} from Telegram: {e}")
