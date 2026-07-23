from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    yield


app = FastAPI(title="Сервис скачивания и анализа файлов", lifespan=lifespan)

app.include_router(web_router)
