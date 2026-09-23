# ☁️ TG Cloud Drive — Персональное облако в Telegram

**TG Cloud Drive** — это полноценное веб-приложение («Google Диск») и Telegram-бот, использующие Telegram в качестве бесплатного безлимитного хранилища файлов.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![Telegram Mini App](https://img.shields.io/badge/Telegram-Mini_App-26A5E4?style=flat&logo=telegram&logoColor=white)

---

## 🌟 Основные возможности

- 🚀 **Файлы до 2 ГБ:** Прямая загрузка и потоковое скачивание через MTProto API (Pyrogram) без ограничений стандартного Bot API (20 МБ).
- 📱 **Поддержка ПК и Смартфонов:** Работает в любом современном браузере или прямо внутри Telegram (как Telegram Web App / Mini App).
- 🎨 **Удобный веб-интерфейс:**
  - Drag & Drop загрузка файлов.
  - Прогресс-бар загрузки в реальном времени.
  - Быстрый поиск файлов по названию.
  - Автоматическое определение типов файлов и иконок.
  - Удаление и скачивание в 1 клик.
- 🔒 **Приватность:** Все файлы хранятся только в вашем личном закрытом Telegram-канале.
- 🛠️ **Бесплатный хостинг:** Легкий деплой за 5 минут на **Render.com**, **Railway** или **Koyeb** через GitHub.

---

## 📖 Полное пошаговое руководство по настройке

### Шаг 1. Подготовка Telegram бота и канала

1. **Создание бота:**
   - Откройте бота [@BotFather](https://t.me/BotFather) в Telegram.
   - Напишите команду `/newbot`, укажите имя и username для бота.
   - Скопируйте полученный **`BOT_TOKEN`** (сохраните его).

2. **Получение API_ID и API_HASH:**
   - Перейдите на официальный сайт [my.telegram.org](https://my.telegram.org).
   - Авторизуйтесь под своим номером телефона.
   - Перейдите в раздел **API development tools**.
   - Создайте новое приложение (любое имя и короткое имя).
   - Скопируйте **`API_ID`** (число) и **`API_HASH`** (строка).

3. **Создание приватного канала хранилища:**
   - Создайте в Telegram **приватный канал** (например, `Мое Хранилище`).
   - Добавьте созданного бота в администраторы этого канала (с правами на публикацию сообщений).
   - Перешлите любое сообщение из канала боту [@userinfobot](https://t.me/userinfobot) или [@RawDataBot](https://t.me/rawdatabot), чтобы узнать **`CHANNEL_ID`** (обычно начинается с `-100...`).

---

### Шаг 2. Локальная проверка и запуск (на ПК)

1. Клонируйте репозиторий или скачайте папку с проектом.
2. Создайте файл `.env` в корневой папке проекта на основе `.env.example`:

   ```env
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   API_ID=123456
   API_HASH=0123456789abcdef0123456789abcdef
   CHANNEL_ID=-1001234567890
   PORT=8000
   ```

3. Установите зависимости Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Запустите сервер:
   ```bash
   python main.py
   ```

5. Откройте в браузере: `http://localhost:8000`

---

### Шаг 3. Загрузка проекта на GitHub

1. Зарегистрируйтесь / войдите на [GitHub.com](https://github.com).
2. Создайте новый публичный или приватный репозиторий `tg-cloud-drive`.
3. Загрузите файлы проекта в репозиторий через терминал:
   ```bash
   git init
   git add .
   git commit -m "Initial commit TG Cloud Drive"
   git branch -M main
   git remote add origin https://github.com/ВАШ_НИК/tg-cloud-drive.git
   git push -u origin main
   ```
   *(Или воспользуйтесь кнопкой **Add file -> Upload files** на странице GitHub)*.

---

### Шаг 4. Бесплатный деплой на Render.com

1. Зарегистрируйтесь на бесплатном хостинге [Render.com](https://render.com) через GitHub.
2. Нажмите кнопку **New +** -> выберите **Web Service**.
3. Выберите ваш GitHub-репозиторий `tg-cloud-drive`.
4. Настройте параметры:
   - **Name:** `my-tg-drive` (любое имя).
   - **Language:** `Docker` (или `Python 3`).
   - **Region:** Любой (например, Frankfurt).
   - **Instance Type:** `Free`.
5. Прокрутите вниз до раздела **Environment Variables** и добавьте следующие переменные:
   - `BOT_TOKEN` = ваш токен от BotFather
   - `API_ID` = ваш API ID от my.telegram.org
   - `API_HASH` = ваш API Hash от my.telegram.org
   - `CHANNEL_ID` = ID вашего приватного канала (`-100...`)
   - `WEB_APP_URL` = URL вашего сервиса на Render (появится вверху экрана, например `https://my-tg-drive.onrender.com`)
6. Нажмите **Create Web Service**. Начнется сборка и запуск!

---

### Шаг 5. Привязка веб-приложения к кнопке в Telegram (Mini App)

1. Вернитесь в [@BotFather](https://t.me/BotFather).
2. Отправьте команду `/setmenubutton`.
3. Выберите вашего бота.
4. Введите URL вашего приложения на Render (например, `https://my-tg-drive.onrender.com`).
5. Укажите название кнопки, например: `☁️ TG Drive`.

✨ **Готово!** Теперь при входе в бота вы и ваши пользователи смогут открыть облачный диск в 1 клик прямо внутри Telegram!

---

## 🏗️ Структура проекта

```
TGBOT/
├── main.py                # FastAPI приложение и эндпоинты
├── config.py              # Конфигурация из переменных окружения (.env)
├── database.py            # SQLite база данных метаданных файлов
├── tg_client.py           # Взаимодействие с Telegram через MTProto (Pyrogram)
├── bot.py                 # Логика Telegram-бота (/start, /help)
├── requirements.txt       # Зависимости Python
├── Dockerfile             # Docker-контейнер для деплоя на хостинг
├── .env.example           # Шаблон переменных окружения
└── static/
    ├── index.html         # Адаптивный веб-интерфейс
    ├── style.css          # Стили темной темы и интерфейса
    └── app.js             # Логика загрузки, поиска и скачивания
```
