import os
import mimetypes
import zipfile
import tarfile
import aiofiles
from typing import Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Response, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    import py7zr
except ImportError:
    py7zr = None

from config import UPLOAD_DIR
from database import (
    init_db,
    add_or_update_file,
    get_db_files,
    move_to_trash,
    restore_from_trash,
    delete_file_record,
    get_trashed_ids_list,
    empty_trash_records,
    create_folder,
    get_folders,
    get_all_folders_flat,
    delete_folder,
    get_breadcrumbs,
    move_file_to_folder,
)
from tg_client import (
    tg_app,
    start_tg_client,
    stop_tg_client,
    upload_to_channel,
    stream_file_from_channel,
    delete_from_channel,
    get_file_category,
    download_file_to_temp,
    STORAGE_CHAT_ID
)

class FolderCreateRequest(BaseModel):
    name: str
    parent_id: Optional[int] = None

class FileMoveRequest(BaseModel):
    message_id: int
    folder_id: Optional[int] = None

def guess_safe_mime_type(filename: str, fallback_mime: str = "") -> str:
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ["jpg", "jpeg"]:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "gif":
        return "image/gif"
    if ext == "webp":
        return "image/webp"
    if ext == "svg":
        return "image/svg+xml"
    if ext == "bmp":
        return "image/bmp"
    if ext == "ico":
        return "image/x-icon"
    if ext in ["mp4", "m4v"]:
        return "video/mp4"
    if ext == "webm":
        return "video/webm"
    if ext in ["mov", "quicktime"]:
        return "video/quicktime"
    if ext == "mkv":
        return "video/x-matroska"
    if ext in ["mp3"]:
        return "audio/mpeg"
    if ext in ["ogg"]:
        return "audio/ogg"
    if ext in ["wav"]:
        return "audio/wav"
    if ext in ["flac"]:
        return "audio/flac"
    if ext in ["aac", "m4a"]:
        return "audio/aac"
    if ext == "pdf":
        return "application/pdf"
    if ext in ["txt", "log", "py", "js", "html", "css", "json", "md", "csv", "xml", "ts", "sh", "yaml", "yml", "ini", "conf", "sql"]:
        return "text/plain; charset=utf-8"
    if ext in ["docx"]:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in ["doc"]:
        return "application/msword"
    if ext in ["zip"]:
        return "application/zip"
    if ext in ["7z"]:
        return "application/x-7z-compressed"
    if ext in ["tar"]:
        return "application/x-tar"
    
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or fallback_mime or "application/octet-stream"

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

# --- Folders API ---
@app.get("/api/folders")
async def list_folders(parent_id: Optional[int] = Query(None)):
    folders = await get_folders(parent_id=parent_id)
    breadcrumbs = await get_breadcrumbs(folder_id=parent_id) if parent_id else []
    return {
        "folders": folders,
        "breadcrumbs": breadcrumbs
    }

@app.get("/api/folders/all")
async def list_all_folders():
    return await get_all_folders_flat()

@app.post("/api/folders")
async def create_new_folder(data: FolderCreateRequest):
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Folder name is required")
    folder_id = await create_folder(name=data.name.strip(), parent_id=data.parent_id)
    return {"id": folder_id, "name": data.name.strip(), "parent_id": data.parent_id}

@app.delete("/api/folders/{folder_id}")
async def remove_folder(folder_id: int):
    await delete_folder(folder_id)
    return {"status": "success", "message": "Folder deleted"}

@app.post("/api/files/move")
async def move_file(data: FileMoveRequest):
    await move_file_to_folder(message_id=data.message_id, folder_id=data.folder_id)
    return {"status": "success", "message": "File moved successfully"}

# --- Files API ---
@app.get("/api/files")
async def list_files(
    search: str = Query(None),
    category: str = Query("all"),
    folder_id: Optional[int] = Query(None)
):
    return await get_db_files(search_query=search, category=category, folder_id=folder_id)

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None)
):
    safe_filename = os.path.basename(file.filename)
    temp_path = os.path.abspath(os.path.join(UPLOAD_DIR, safe_filename))
    
    try:
        async with aiofiles.open(temp_path, "wb") as out_file:
            while chunk := await file.read(4 * 1024 * 1024):
                await out_file.write(chunk)
            await out_file.flush()

        file_size = os.path.getsize(temp_path)
        message_id = await upload_to_channel(temp_path, safe_filename)
        category = get_file_category(safe_filename, file.content_type)

        await add_or_update_file(
            message_id=message_id,
            filename=safe_filename,
            file_size=file_size,
            mime_type=file.content_type,
            category=category,
            folder_id=folder_id
        )

        return {
            "id": message_id,
            "filename": safe_filename,
            "file_size": file_size,
            "folder_id": folder_id,
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
        mime_type = guess_safe_mime_type(filename, getattr(media, "mime_type", ""))

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        if file_size > 0:
            headers["Content-Length"] = str(file_size)

        return StreamingResponse(
            stream_file_from_channel(message_id),
            media_type=mime_type,
            headers=headers
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Cannot download file: {e}")

@app.get("/api/raw/{message_id}")
async def raw_inline_file(message_id: int):
    """Serves file inline with proper content-type for in-browser preview (images, video, audio, pdf, doc)."""
    target_chat = STORAGE_CHAT_ID or os.getenv("CHANNEL_ID")
    try:
        msg = await tg_app.get_messages(target_chat, message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="File not found")

        media = msg.document or msg.video or msg.audio or msg.photo
        filename = getattr(media, "file_name", None)
        if not filename:
            if msg.photo:
                filename = f"photo_{message_id}.jpg"
            elif msg.video:
                filename = f"video_{message_id}.mp4"
            elif msg.audio:
                filename = f"audio_{message_id}.mp3"
            else:
                filename = f"file_{message_id}"

        file_size = getattr(media, "file_size", 0)
        mime_type = guess_safe_mime_type(filename, getattr(media, "mime_type", ""))

        headers = {
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
        }
        if file_size > 0:
            headers["Content-Length"] = str(file_size)

        return StreamingResponse(
            stream_file_from_channel(message_id),
            media_type=mime_type,
            headers=headers
        )
    except Exception as e:
        print(f"Cannot serve raw file {message_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Cannot load file: {e}")

@app.get("/api/inspect/{message_id}")
async def inspect_file_endpoint(message_id: int):
    """Inspects archives (zip, 7z, tar) or text/doc files to return file tree / content."""
    target_chat = STORAGE_CHAT_ID or os.getenv("CHANNEL_ID")
    try:
        msg = await tg_app.get_messages(target_chat, message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="File not found")

        media = msg.document or msg.video or msg.audio or msg.photo
        filename = getattr(media, "file_name", f"file_{message_id}")
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        file_size = getattr(media, "file_size", 0)

        # Temporary file for inspection
        temp_name = f"inspect_{message_id}_{os.path.basename(filename)}"
        temp_path = os.path.abspath(os.path.join(UPLOAD_DIR, temp_name))

        await download_file_to_temp(message_id, temp_path)

        try:
            # 1. Check for 7z
            if ext == "7z" and py7zr:
                try:
                    with py7zr.SevenZipFile(temp_path, mode='r') as z7:
                        entries = [
                            {"name": f.filename, "size": f.uncompressed, "is_dir": f.is_directory}
                            for f in z7.list()
                        ]
                        return {"type": "archive", "format": "7z", "filename": filename, "entries": entries}
                except Exception as e7:
                    print(f"py7zr inspection failed: {e7}")

            # 2. Check for zip (or docx)
            if ext in ["zip", "docx", "jar", "apk"] or zipfile.is_zipfile(temp_path):
                try:
                    with zipfile.ZipFile(temp_path, 'r') as zf:
                        entries = [
                            {"name": item.filename, "size": item.file_size, "is_dir": item.is_dir()}
                            for item in zf.infolist()
                        ]
                        return {"type": "archive", "format": "zip", "filename": filename, "entries": entries}
                except Exception as ez:
                    print(f"zip inspection failed: {ez}")

            # 3. Check for tar / tar.gz / tar.bz2
            if ext in ["tar", "gz", "bz2", "xz", "tgz"] or tarfile.is_tarfile(temp_path):
                try:
                    with tarfile.open(temp_path, 'r:*') as tf:
                        entries = [
                            {"name": m.name, "size": m.size, "is_dir": m.isdir()}
                            for m in tf.getmembers()
                        ]
                        return {"type": "archive", "format": "tar", "filename": filename, "entries": entries}
                except Exception as et:
                    print(f"tar inspection failed: {et}")

            # 4. Check for text or doc
            if ext in ["txt", "log", "py", "js", "html", "css", "json", "md", "csv", "xml", "doc"]:
                try:
                    async with aiofiles.open(temp_path, "r", encoding="utf-8", errors="ignore") as tf:
                        sample = await tf.read(100000)
                    return {"type": "text", "filename": filename, "content": sample}
                except Exception as ex_txt:
                    print(f"text inspection failed: {ex_txt}")

            return {
                "type": "unsupported",
                "filename": filename,
                "message": f"Preview not supported for format: {ext}"
            }

        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    except Exception as e:
        print(f"Inspection error for {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    trash_ids = await get_trashed_ids_list()
    for mid in trash_ids:
        try:
            await delete_from_channel(mid)
        except Exception:
            pass
    await empty_trash_records()
    return {"status": "success", "message": "Trash emptied"}

@app.delete("/api/files/{message_id}")
async def delete_file_permanently(message_id: int):
    await delete_from_channel(message_id)
    await delete_file_record(message_id)
    return {"status": "success", "message": "File permanently deleted"}
