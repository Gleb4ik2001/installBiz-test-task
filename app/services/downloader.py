import io
import json
import os
import zipfile
from datetime import datetime

import aiosqlite
import httpx
import pytz

from app.config import settings
from app.services.analyzer import analyze_digits
from app.services.api_client import APIClient

# Глобальное состояние процесса скачивания (в памяти)
download_state = {
    "is_running": False,
    "start_time_nsk": None,
    "found_names_count": 0,
    "downloaded_count": 0,
    "status_message": "Процесс не запущен",
    "error_message": None,
    "retry_after": 0,
}


async def run_download_pipeline():
    global download_state
    download_state["is_running"] = True
    download_state["error_message"] = None

    # Замер времени старта по Новосибирску (НСК)
    nsk_tz = pytz.timezone("Asia/Novosibirsk")
    start_time = datetime.now(nsk_tz)
    download_state["start_time_nsk"] = start_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    download_state["status_message"] = "Скачивание в процессе..."

    api_client = APIClient(download_state)

    async with httpx.AsyncClient(
        base_url=settings.TARGET_API_URL, timeout=60.0
    ) as client:
        try:
            while True:
                # 1. GET /api/files/names — Запрос порции имён
                download_state["status_message"] = "Запрос имён файлов..."
                res = await api_client.safe_request(client, "GET", "/api/files/names")
                data = res.json()
                file_names = data.get("file_names", [])

                # Пустой список означают завершение каталога
                if not file_names:
                    download_state["status_message"] = "Каталог полностью скачан!"
                    break

                download_state["found_names_count"] += len(file_names)

                # 2. POST /api/files/download — Скачивание (батчи строго по 3 файла)
                chunk_size = 3
                for i in range(0, len(file_names), chunk_size):
                    chunk = file_names[i : i + chunk_size]
                    download_state["status_message"] = (
                        f"Скачивание {len(chunk)} файлов..."
                    )

                    dl_res = await api_client.safe_request(
                        client,
                        "POST",
                        "/api/files/download",
                        json={"file_names": chunk},
                    )

                    # Распаковка ZIP, сохранения и расчет статистики
                    zip_data = io.BytesIO(dl_res.content)
                    with zipfile.ZipFile(zip_data) as zf:
                        async with aiosqlite.connect(settings.DB_PATH) as db:
                            for fname in zf.namelist():
                                file_content = zf.read(fname).decode(
                                    "utf-8", errors="ignore"
                                )

                                # Сохранение на диск
                                file_path = os.path.join(settings.DOWNLOAD_DIR, fname)
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(file_content)

                                # Анализ текста
                                stats = analyze_digits(file_content)
                                download_dt = datetime.now(nsk_tz).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )

                                # Запись в БД
                                await db.execute(
                                    """
                                    INSERT INTO files (filename, downloaded_at, stats_json)
                                    VALUES (?, ?, ?)
                                    ON CONFLICT(filename) DO UPDATE SET
                                        downloaded_at=excluded.downloaded_at,
                                        stats_json=excluded.stats_json
                                """,
                                    (fname, download_dt, json.dumps(stats)),
                                )

                                download_state["downloaded_count"] += 1
                            await db.commit()

                    # 3. POST /api/files/downloaded — Отметка о скачивании
                    download_state["status_message"] = (
                        "Подтверждение скачанных файлов..."
                    )
                    await api_client.safe_request(
                        client,
                        "POST",
                        "/api/files/downloaded",
                        json={"file_names": chunk},
                    )

        except Exception as e:
            download_state["status_message"] = (
                f"Процесс остановлен из-за ошибки: {str(e)}"
            )
        finally:
            download_state["is_running"] = False
