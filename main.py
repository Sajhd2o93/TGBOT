import os
import aiofiles
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import UPLOAD_DIR, PORT
from database import init_db, add_file, get_all_files, get_file_by_id, delete_file_by_id
from tg_client import tg_app, start_tg_client, stop_tg_client, upload_to_channel, stream_file_from_channel, delete_from_channel
from bot import register_bot_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("🚀 Initializing SQLite database...")
    try:
        await init_db()
    except Exception as e:
        print(f"Database init error: {e}")
    
    print("🤖 Registering Telegram bot handlers...")
    try:
        register_bot_handlers(tg_app)
    except Exception as e:
        print(f"Bot handlers registration error: {e}")
    
    print("⚡ Starting Telegram MTProto client...")
    await start_tg_client()
    
    yield
    
    # Shutdown logic
    print("🛑 Stopping Telegram client...")
    await stop_tg_client()

app = FastAPI(title="Telegram Cloud Drive", lifespan=lifespan)

# Detailed Request/Response Logging Middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        print(f"📤 [HTTP {response.status_code}] {request.method} {request.url.path} | Time: {process_time:.1f}ms | Client: {client_ip}")
        return response
    except Exception as e:
        print(f"❌ [HTTP EXCEPTION] {request.method} {request.url.path} -> {type(e).__name__}: {str(e)}")
        raise e

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    async with aiofiles.open("static/index.html", "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/health")
async def health_check():
    return {"status": "ok", "tg_connected": tg_app.is_connected}

@app.get("/api/files")
async def list_files(search: str = Query(None)):
    files = await get_all_files(search_query=search)
    return files

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

        file_id = await add_file(
            filename=safe_filename,
            file_size=file_size,
            mime_type=file.content_type,
            message_id=message_id
        )

        return {
            "id": file_id,
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

@app.get("/api/download/{file_id}")
async def download_file(file_id: int):
    file_info = await get_file_by_id(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    filename = file_info["filename"]
    mime_type = file_info["mime_type"] or "application/octet-stream"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(file_info["file_size"])
    }

    return StreamingResponse(
        stream_file_from_channel(file_info["message_id"]),
        media_type=mime_type,
        headers=headers
    )

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int):
    message_id = await delete_file_by_id(file_id)
    if not message_id:
        raise HTTPException(status_code=404, detail="File not found in database")

    await delete_from_channel(message_id)
    return {"status": "success", "message": "File deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
