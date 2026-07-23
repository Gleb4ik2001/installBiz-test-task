import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TARGET_API_URL: str = "http://91.199.149.128:18001"
    CANDIDATE_ID: str = "fsdn43fb4b3f"
    DOWNLOAD_DIR: str = "downloaded_files"
    DB_PATH: str = "database.db"

    class Config:
        env_file = ".env"

settings = Settings()

# Создаем папку для загрузок, если она отсутствует
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)