from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.models.company import Company
from app.models.metric import Metric
from app.services.metric_calculator import MetricCalculator

router = APIRouter()


# 👇 ВСЕ ПОЛЯ ДЕЛАЕМ Optional (могут быть None)
class MetricResponse(BaseModel):
    id: int
    company_id: int
    calculation_date: date
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    eps: Optional[float] = None
    book_value_per_share: Optional[float] = None
    dividend_per_share: Optional[float] = None
    dividend_yield: Optional[float] = None

    class Config:
        from_attributes = True


@router.post("/metrics/calculate/{ticker}")
async def calculate_metrics(
        ticker: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Рассчитать мультипликаторы для компании
    """
    # Находим компанию
    result = await db.execute(
        select(Company).where(Company.ticker == ticker)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    # Рассчитываем метрики
    metrics = await MetricCalculator.calculate_metrics(company.id, db)

    if "error" in metrics:
        raise HTTPException(status_code=400, detail=metrics["error"])

    return {
        "ticker": ticker,
        "company": company.name,
        "metrics": metrics,
        "calculated_date": date.today().isoformat()
    }


@router.get("/metrics/all")
async def get_all_metrics(
        db: AsyncSession = Depends(get_db)
):
    """
    Получить мультипликаторы для всех компаний (с тикером и названием)
    """
    result = await db.execute(
        select(
            Metric,
            Company.ticker,
            Company.name,
        )
        .join(Company, Metric.company_id == Company.id)
        .order_by(Metric.calculation_date.desc())
    )
    rows = result.all()

    return [
        {
            "ticker": ticker,
            "company_name": name,
            "pe_ratio": m.pe_ratio,
            "pb_ratio": m.pb_ratio,
            "roe": m.roe,
            "eps": m.eps,
            "book_value_per_share": m.book_value_per_share,
            "dividend_yield": m.dividend_yield,
            "dividend_per_share": m.dividend_per_share,
            "calculation_date": m.calculation_date.isoformat(),
        }
        for m, ticker, name in rows
    ]


@router.get("/metrics/{ticker}", response_model=MetricResponse)
async def get_metrics(
        ticker: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить последние мультипликаторы для компании
    """
    # Находим компанию
    result = await db.execute(
        select(Company).where(Company.ticker == ticker)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    # Получаем последние метрики
    metrics = await MetricCalculator.get_latest_metrics(company.id, db)

    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for {ticker}. Run /metrics/calculate first"
        )

    return metrics
