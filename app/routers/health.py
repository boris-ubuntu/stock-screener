from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    app_name: str
    debug_mode: bool


class DetailedHealthResponse(HealthResponse):
    db_connected: bool


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    logger.info("Health check")
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now().isoformat(),
        app_name=settings.APP_NAME,
        debug_mode=settings.DEBUG,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
):
    """Проверка здоровья с проверкой подключения к БД."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return DetailedHealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.now().isoformat(),
        app_name=settings.APP_NAME,
        debug_mode=settings.DEBUG,
        db_connected=db_ok,
    )

