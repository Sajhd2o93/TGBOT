import aiosqlite
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Folders table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Files table with folder_id
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                message_id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                category TEXT DEFAULT 'other',
                folder_id INTEGER DEFAULT NULL,
                is_trashed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            )
        """)
        # Safe migration if folder_id does not exist
        try:
            await db.execute("ALTER TABLE files ADD COLUMN folder_id INTEGER DEFAULT NULL")
        except Exception:
            pass  # column already exists
        await db.commit()

# --- Folders CRUD ---
async def create_folder(name: str, parent_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO folders (name, parent_id) VALUES (?, ?)",
            (name.strip(), parent_id if parent_id and parent_id > 0 else None)
        )
        await db.commit()
        return cursor.lastrowid

async def get_folders(parent_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if parent_id and parent_id > 0:
            cursor = await db.execute("SELECT * FROM folders WHERE parent_id = ? ORDER BY name ASC", (parent_id,))
        else:
            cursor = await db.execute("SELECT * FROM folders WHERE parent_id IS NULL ORDER BY name ASC")
        rows = await cursor.fetchall()
        
        result = []
        for r in rows:
            # Count files inside folder
            fc = await db.execute("SELECT COUNT(*) FROM files WHERE folder_id = ? AND is_trashed = 0", (r["id"],))
            file_count = (await fc.fetchone())[0]
            result.append({
                "id": r["id"],
                "name": r["name"],
                "parent_id": r["parent_id"],
                "created_at": r["created_at"],
                "file_count": file_count
            })
        return result

async def get_all_folders_flat():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name, parent_id FROM folders ORDER BY name ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def delete_folder(folder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Move files in this folder to root (folder_id = NULL)
        await db.execute("UPDATE files SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
        # Move subfolders to root
        await db.execute("UPDATE folders SET parent_id = NULL WHERE parent_id = ?", (folder_id,))
        await db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        await db.commit()

async def get_breadcrumbs(folder_id: int):
    breadcrumbs = []
    curr_id = folder_id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        while curr_id and curr_id > 0:
            cursor = await db.execute("SELECT id, name, parent_id FROM folders WHERE id = ?", (curr_id,))
            row = await cursor.fetchone()
            if not row:
                break
            breadcrumbs.insert(0, {"id": row["id"], "name": row["name"]})
            curr_id = row["parent_id"]
    return breadcrumbs

# --- Files CRUD with Folder support ---
async def add_or_update_file(message_id: int, filename: str, file_size: int, mime_type: str, category: str, created_at: str = None, folder_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        f_id = folder_id if folder_id and folder_id > 0 else None
        if created_at:
            await db.execute("""
                INSERT INTO files (message_id, filename, file_size, mime_type, category, folder_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    filename=excluded.filename,
                    file_size=excluded.file_size,
                    mime_type=excluded.mime_type,
                    category=excluded.category,
                    folder_id=COALESCE(excluded.folder_id, files.folder_id)
            """, (message_id, filename, file_size, mime_type, category, f_id, created_at))
        else:
            await db.execute("""
                INSERT INTO files (message_id, filename, file_size, mime_type, category, folder_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    filename=excluded.filename,
                    file_size=excluded.file_size,
                    mime_type=excluded.mime_type,
                    category=excluded.category,
                    folder_id=COALESCE(excluded.folder_id, files.folder_id)
            """, (message_id, filename, file_size, mime_type, category, f_id))
        await db.commit()

async def move_file_to_folder(message_id: int, folder_id: int = None):
    f_id = folder_id if folder_id and folder_id > 0 else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE files SET folder_id = ? WHERE message_id = ?", (f_id, message_id))
        await db.commit()

async def get_db_files(search_query: str = None, category: str = "all", folder_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if category == "trash":
            query = "SELECT * FROM files WHERE is_trashed = 1"
            params = []
        else:
            query = "SELECT * FROM files WHERE is_trashed = 0"
            params = []
            
            # If viewing standard folder hierarchy in "all" category
            if category == "all" and not search_query:
                if folder_id and folder_id > 0:
                    query += " AND folder_id = ?"
                    params.append(folder_id)
                else:
                    query += " AND folder_id IS NULL"
            elif category and category != "all":
                query += " AND category = ?"
                params.append(category)

        if search_query:
            query += " AND filename LIKE ?"
            params.append(f"%{search_query}%")

        query += " ORDER BY message_id DESC"
        
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        
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
                "folder_id": r["folder_id"],
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
