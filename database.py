import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trash (
                message_id INTEGER PRIMARY KEY,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_trashed_ids() -> set:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT message_id FROM trash")
        rows = await cursor.fetchall()
        return {row[0] for row in rows}

async def move_to_trash(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO trash (message_id) VALUES (?)", (message_id,))
        await db.commit()

async def restore_from_trash(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trash WHERE message_id = ?", (message_id,))
        await db.commit()

async def remove_from_trash_table(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trash WHERE message_id = ?", (message_id,))
        await db.commit()

async def get_all_trash_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT message_id FROM trash")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def empty_trash_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM trash")
        await db.commit()
