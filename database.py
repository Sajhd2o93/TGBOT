import aiosqlite
import os
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                message_id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                category TEXT DEFAULT 'other',
                is_trashed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_or_update_file(message_id: int, filename: str, file_size: int, mime_type: str, category: str, created_at: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if created_at:
            await db.execute("""
                INSERT INTO files (message_id, filename, file_size, mime_type, category, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    filename=excluded.filename,
                    file_size=excluded.file_size,
                    mime_type=excluded.mime_type,
                    category=excluded.category
            """, (message_id, filename, file_size, mime_type, category, created_at))
        else:
            await db.execute("""
                INSERT INTO files (message_id, filename, file_size, mime_type, category)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    filename=excluded.filename,
                    file_size=excluded.file_size,
                    mime_type=excluded.mime_type,
                    category=excluded.category
            """, (message_id, filename, file_size, mime_type, category))
        await db.commit()

async def get_db_files(search_query: str = None, category: str = "all"):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Base query
        if category == "trash":
            query = "SELECT * FROM files WHERE is_trashed = 1"
            params = []
        else:
            query = "SELECT * FROM files WHERE is_trashed = 0"
            params = []
            if category and category != "all":
                query += " AND category = ?"
                params.append(category)

        if search_query:
            query += " AND filename LIKE ?"
            params.append(f"%{search_query}%")

        query += " ORDER BY message_id DESC"
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
        # Get counts
        c_active = await db.execute("SELECT COUNT(*) FROM files WHERE is_trashed = 0")
        total_active = (await c_active.fetchone())[0]
        
        c_trash = await db.execute("SELECT COUNT(*) FROM files WHERE is_trashed = 1")
        total_trash = (await c_trash.fetchone())[0]

        files_list = []
        for r in rows:
            files_list.append({
                "id": r["message_id"],
                "filename": r["filename"],
                "file_size": r["file_size"],
                "mime_type": r["mime_type"],
                "category": r["category"],
                "message_id": r["message_id"],
                "created_at": r["created_at"]
            })

        return {
            "files": files_list,
            "total_active": total_active,
            "total_trash": total_trash
        }

async def move_to_trash(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE files SET is_trashed = 1 WHERE message_id = ?", (message_id,))
        await db.commit()

async def restore_from_trash(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE files SET is_trashed = 0 WHERE message_id = ?", (message_id,))
        await db.commit()

async def delete_file_record(message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM files WHERE message_id = ?", (message_id,))
        await db.commit()

async def get_trashed_ids_list():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT message_id FROM files WHERE is_trashed = 1")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def empty_trash_records():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM files WHERE is_trashed = 1")
        await db.commit()
