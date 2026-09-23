import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

PORT = int(os.getenv("PORT", "8000"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "")

# Directory to temporarily store uploads before sending to Telegram
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database path
DB_PATH = os.getenv("DB_PATH", "tg_cloud.db")
