from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import WEB_APP_URL

def register_bot_handlers(app: Client):
    @app.on_message(filters.command("start") & filters.private)
    async def start_handler(client, message):
        buttons = []
        if WEB_APP_URL:
            buttons.append([InlineKeyboardButton("☁️ Открыть TG Drive", web_app=WebAppInfo(url=WEB_APP_URL))])
        
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        
        text = (
            "👋 **Добро пожаловать в Telegram Cloud Drive!**\n\n"
            "📁 Это ваше личное облачное хранилище на базе Telegram.\n"
            "🚀 Вы можете загружать файлы до 2 ГБ и получать к ним доступ с любого устройства (ПК / Телефон).\n\n"
            "Нажмите кнопку ниже, чтобы открыть веб-интерфейс Диска!"
        )
        await message.reply_text(text, reply_markup=reply_markup)

    @app.on_message(filters.command("help") & filters.private)
    async def help_handler(client, message):
        await message.reply_text(
            "ℹ️ **Инструкция по использованию:**\n\n"
            "1. Нажмите кнопку **Открыть TG Drive**.\n"
            "2. Перетащите файлы или выберите их для загрузки.\n"
            "3. Все файлы сохраняются в ваш закрытый канал Telegram.\n"
            "4. Скачивайте файлы в любой момент без ограничений скорости."
        )
