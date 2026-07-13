from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import companies, health, financial_reports, prices, metrics, charts, import_reports, parse_reports
from app.core.database import engine, Base
from app.core.config import settings
from app.routers import currency
from app.routers import loader

import os
import logging

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск")
    logger.info("Version: {}".format(settings.APP_VERSION))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы созданы")
    app.state.startup_time = "just now"
    yield
    logger.info("Остановка")
    await engine.dispose()


app = FastAPI(
    title="Stock screener",
    description="Stock screener",
    version="0.1.0",
    lifespan=lifespan
)

# Подключаем роутеры
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(companies.router, prefix="/api/v1", tags=["companies"])
app.include_router(financial_reports.router, prefix="/api/v1", tags=["financial_reports"])
app.include_router(prices.router, prefix="/api/v1", tags=["prices"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
app.include_router(charts.router, prefix="/api/v1", tags=["charts"])
app.include_router(import_reports.router, prefix="/api/v1", tags=["import"])
app.include_router(parse_reports.router, prefix="/api/v1", tags=["parse"])
app.include_router(currency.router, prefix="/api/v1", tags=["currency"])
app.include_router(loader.router, prefix="/api/v1", tags=["loader"])
# --- ФРОНТЕНД ---

# Подключаем папку со статическими файлами (CSS, JS)
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    """Отдает главную страницу фронтенда"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "static", "frontend", "index.html")

    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {
            "message": "Stock screener API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "frontend": "Frontend not found. Please create static/frontend/index.html"
        }