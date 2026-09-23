import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_file(filename: str, file_size: int, mime_type: str, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO files (filename, file_size, mime_type, message_id)
            VALUES (?, ?, ?, ?)
            """,
            (filename, file_size, mime_type, message_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_all_files(search_query: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if search_query:
            cursor = await db.execute(
                "SELECT * FROM files WHERE filename LIKE ? ORDER BY created_at DESC",
                (f"%{search_query}%",)
            )
        else:
            cursor = await db.execute("SELECT * FROM files ORDER BY created_at DESC")
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_file_by_id(file_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def delete_file_by_id(file_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT message_id FROM files WHERE id = ?", (file_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        message_id = row[0]
        await db.execute("DELETE FROM files WHERE id = ?", (file_id,))
        await db.commit()
        return message_id
