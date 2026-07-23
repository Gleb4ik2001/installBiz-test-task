import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TARGET_API_URL: str
    CANDIDATE_ID: str
    DOWNLOAD_DIR: str
    DB_PATH: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

# Создаем папку для загрузок, если она отсутствует
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
