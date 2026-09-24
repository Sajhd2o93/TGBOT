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

async def start_tg_client():
    global _is_started
    if _is_started or tg_app.is_connected:
        return True

    if not BOT_TOKEN or not API_ID or not API_HASH or API_ID == 0:
        print("⚠️ WARNING: BOT_TOKEN, API_ID, or API_HASH is missing in Environment Variables!")
        return False
    try:
        await tg_app.start()
        _is_started = True
        me = await tg_app.get_me()
        print(f"✅ Telegram Bot @{me.username} (ID: {me.id}) connected successfully!")
        
        # Test access to channel
        try:
            chat = await tg_app.get_chat(CHANNEL_ID)
            print(f"✅ Channel storage verified: '{chat.title}' (ID: {CHANNEL_ID})")
        except Exception as e:
            print(f"⚠️ Warning regarding CHANNEL_ID ({CHANNEL_ID}): {e}")
            print("👉 Please ensure the bot is added as an ADMINISTRATOR with post permissions to this channel!")
        
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

async def upload_to_channel(file_path: str, filename: str, progress_callback=None):
    """Uploads a file to the Telegram storage channel and returns the message_id."""
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected yet. Check Infrlo logs for FLOOD_WAIT or credentials.")

    print(f"📤 Uploading '{filename}' to Telegram channel ({CHANNEL_ID})...")
    try:
        msg = await tg_app.send_document(
            chat_id=CHANNEL_ID,
            document=file_path,
            file_name=filename,
            caption=f"📁 File: `{filename}`",
            progress=progress_callback
        )
        print(f"✅ File '{filename}' successfully saved to channel. Message ID: {msg.id}")
        return msg.id
    except Exception as e:
        print(f"❌ Telegram send_document failed: {type(e).__name__} - {e}")
        raise ValueError(f"Telegram error: {type(e).__name__} - {str(e)}")

async def stream_file_from_channel(message_id: int):
    """Yields chunks of the file stored in Telegram channel message."""
    if not tg_app.is_connected:
        raise ValueError("Telegram Bot is not connected.")

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
        print(f"🗑️ Deleted message {message_id} from Telegram channel.")
    except Exception as e:
        print(f"Error deleting message {message_id} from Telegram: {e}")
