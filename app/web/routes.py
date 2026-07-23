import json
from typing import List
import aiosqlite
from fastapi import APIRouter, BackgroundTasks, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.downloader import download_state, run_download_pipeline

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")



@router.get("/", response_class=HTMLResponse)
async def page_download(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="download.html",
        context={
            "status_message": download_state.get("status_message", "Процесс не запущен"),
            "start_time_nsk": download_state.get("start_time_nsk", "Не запущен"),
            "found_names_count": download_state.get("found_names_count", 0),
            "downloaded_count": download_state.get("downloaded_count", 0),
            "is_running": download_state.get("is_running", False)
        }
    )

@router.get("/files", response_class=HTMLResponse)
async def page_files(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    offset = (page - 1) * limit
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM files") as cursor:
            row = await cursor.fetchone()
            total_files = row[0] if row else 0

        async with db.execute("""
            SELECT filename, downloaded_at 
            FROM files 
            ORDER BY downloaded_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset)) as cursor:
            files = await cursor.fetchall()

    total_pages = max(1, (total_files + limit - 1) // limit)

    return templates.TemplateResponse(
        request=request,
        name="files.html",
        context={
            "files": files,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "total_files": total_files
        }
    )

# --- API Маршруты ---

@router.post("/api/start-download")
async def start_download(background_tasks: BackgroundTasks):
    if not download_state["is_running"]:
        download_state["found_names_count"] = 0
        download_state["downloaded_count"] = 0
        background_tasks.add_task(run_download_pipeline)
        return {"status": "started"}
    return {"status": "already_running"}

@router.get("/api/download-status")
async def get_status():
    return download_state

@router.post("/api/calculate")
async def calculate_stats(
    selection_type: str = Form(...),  # 'selected', 'page', 'all'
    filenames: List[str] = Form([])
):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        if selection_type == "all":
            async with db.execute("SELECT filename, stats_json FROM files") as cursor:
                rows = await cursor.fetchall()
        else:
            if not filenames:
                return JSONResponse({"error": "Файлы не выбраны"}, status_code=400)
            placeholders = ",".join("?" for _ in filenames)
            async with db.execute(f"SELECT filename, stats_json FROM files WHERE filename IN ({placeholders})", filenames) as cursor:
                rows = await cursor.fetchall()

    total_stats = {str(i): 0 for i in range(10)}
    file_stats = {}

    for fname, stats_json in rows:
        stats = json.loads(stats_json)
        file_stats[fname] = stats
        for d, count in stats.items():
            total_stats[d] += count

    return {
        "processed_count": len(rows),
        "total_stats": total_stats,
        "file_stats": file_stats
    }
