from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Stock Screener"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql://boris:boris@localhost:5432/screener_db"
    MOEX_API_URL: str = "https://iss.moex.com/iss"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()