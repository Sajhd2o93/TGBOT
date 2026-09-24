import os
import aiofiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR
from database import (
    init_db,
    get_trashed_ids,
    move_to_trash,
    restore_from_trash,
    remove_from_trash_table,
    get_all_trash_ids,
    empty_trash_db
)
from tg_client import (
    tg_app,
    start_tg_client,
    stop_tg_client,
    upload_to_channel,
    get_channel_files,
    stream_file_from_channel,
    delete_from_channel,
    STORAGE_CHAT_ID
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing Database...")
    await init_db()
    print("⚡ Starting Telegram MTProto client...")
    await start_tg_client()
    yield
    print("🛑 Stopping Telegram client...")
    await stop_tg_client()

app = FastAPI(title="TG Drive", lifespan=lifespan)

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    async with aiofiles.open("static/index.html", "r", encoding="utf-8") as f:
        content = await f.read()
    return HTMLResponse(content=content, headers=response.headers)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/files")
async def list_files(search: str = Query(None), category: str = Query("all")):
    all_files = await get_channel_files(search_query=search)
    trashed_ids = await get_trashed_ids()

    if category == "trash":
        result = [f for f in all_files if f["id"] in trashed_ids]
    else:
        active_files = [f for f in all_files if f["id"] not in trashed_ids]
        if category and category != "all":
            result = [f for f in active_files if f.get("category") == category]
        else:
            result = active_files

    return {
        "files": result,
        "total_active": len([f for f in all_files if f["id"] not in trashed_ids]),
        "total_trash": len([f for f in all_files if f["id"] in trashed_ids])
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_filename = os.path.basename(file.filename)
    temp_path = os.path.abspath(os.path.join(UPLOAD_DIR, safe_filename))
    
    try:
        async with aiofiles.open(temp_path, "wb") as out_file:
            while chunk := await file.read(4 * 1024 * 1024):
                await out_file.write(chunk)
            await out_file.flush()

        file_size = os.path.getsize(temp_path)
        message_id = await upload_to_channel(temp_path, safe_filename)

        return {
            "id": message_id,
            "filename": safe_filename,
            "file_size": file_size,
            "message_id": message_id
        }

    except Exception as e:
        print(f"❌ API Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.get("/api/download/{message_id}")
async def download_file(message_id: int):
    target_chat = STORAGE_CHAT_ID or os.getenv("CHANNEL_ID")
    try:
        msg = await tg_app.get_messages(target_chat, message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="File not found")

        media = msg.document or msg.video or msg.audio or msg.photo
        filename = getattr(media, "file_name", f"file_{message_id}")
        file_size = getattr(media, "file_size", 0)
        mime_type = getattr(media, "mime_type", "application/octet-stream")

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(file_size)
        }

        return StreamingResponse(
            stream_file_from_channel(message_id),
            media_type=mime_type,
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Cannot download file: {e}")

@app.post("/api/trash/{message_id}")
async def trash_file(message_id: int):
    await move_to_trash(message_id)
    return {"status": "success", "message": "Moved to trash"}

@app.post("/api/trash/restore/{message_id}")
async def restore_file(message_id: int):
    await restore_from_trash(message_id)
    return {"status": "success", "message": "Restored from trash"}

@app.post("/api/trash/empty")
async def empty_trash():
    trash_ids = await get_all_trash_ids()
    for mid in trash_ids:
        try:
            await delete_from_channel(mid)
        except Exception:
            pass
    await empty_trash_db()
    return {"status": "success", "message": "Trash emptied"}

@app.delete("/api/files/{message_id}")
async def delete_file_permanently(message_id: int):
    await delete_from_channel(message_id)
    await remove_from_trash_table(message_id)
    return {"status": "success", "message": "File permanently deleted"}
