from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
import asyncio
import logging

from app.core.database import get_db
from app.models.company import Company
from app.models.stock_price import StockPrice
from app.services.moex_client import MOEXClient
from app.services.metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/prices/load/{ticker}")
async def load_prices_from_moex(
    ticker: str,
    days: int = 365,
    db: AsyncSession = Depends(get_db),
):
    """Загрузить исторические цены акций с MOEX и сохранить в БД"""
    result = await db.execute(select(Company).where(Company.ticker == ticker))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    to_date = date.today()
    from_date = to_date - timedelta(days=days)

    try:
        logger.info(f"Начинаем загрузку для {ticker} за {days} дней")
        df = await asyncio.wait_for(
            MOEXClient.get_stock_prices(
                ticker=ticker,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Таймаут загрузки данных для {ticker}")

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")

    saved = 0
    updated = 0

    for _, row in df.iterrows():
        existing = await db.execute(
            select(StockPrice).where(
                StockPrice.company_id == company.id,
                StockPrice.date == row["date"],
            )
        )
        existing_price = existing.scalar_one_or_none()

        if existing_price:
            existing_price.open = row["open"]
            existing_price.high = row["high"]
            existing_price.low = row["low"]
            existing_price.close = row["close"]
            existing_price.volume = row["volume"]
            updated += 1
        else:
            price = StockPrice(
                company_id=company.id,
                date=row["date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            db.add(price)
            saved += 1

    await db.commit()

    return {
        "message": f"Price data processed for {ticker}",
        "saved_new": saved,
        "updated_existing": updated,
        "total_records": len(df),
        "date_range": {
            "from": df["date"].min().isoformat(),
            "to": df["date"].max().isoformat(),
        },
    }


@router.get("/prices/company/{company_id}")
async def get_company_prices(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить все цены компании"""
    result = await db.execute(
        select(StockPrice)
        .where(StockPrice.company_id == company_id)
        .order_by(StockPrice.date.asc())
    )
    prices = result.scalars().all()

    return [
        {
            "date": p.date.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices
    ]


@router.post("/update-and-calculate/{ticker}")
async def update_price_and_metrics(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Обновить цены за 365 дней и пересчитать метрики для компании"""
    result = await db.execute(select(Company).where(Company.ticker == ticker))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    to_date = date.today()
    from_date = to_date - timedelta(days=365)
    df = await MOEXClient.get_stock_prices(
        ticker=ticker,
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
    )

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")

    # Сохраняем ВСЕ строки из загруженных данных
    saved = 0
    updated = 0
    for _, row in df.iterrows():
        existing = await db.execute(
            select(StockPrice).where(
                StockPrice.company_id == company.id,
                StockPrice.date == row["date"],
            )
        )
        existing_price = existing.scalar_one_or_none()

        if existing_price:
            existing_price.open = row["open"]
            existing_price.high = row["high"]
            existing_price.low = row["low"]
            existing_price.close = row["close"]
            existing_price.volume = row["volume"]
            updated += 1
        else:
            new_price = StockPrice(
                company_id=company.id,
                date=row["date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            db.add(new_price)
            saved += 1

    await db.commit()

    metrics_result = await MetricCalculator.calculate_metrics(company.id, db)
    if "error" in metrics_result:
        raise HTTPException(status_code=400, detail=metrics_result["error"])

    latest_metrics = await MetricCalculator.get_latest_metrics(company.id, db)
    if not latest_metrics:
        raise HTTPException(status_code=404, detail="Metrics not found after calculation")

    result = await db.execute(
        select(StockPrice)
        .where(StockPrice.company_id == company.id)
        .order_by(StockPrice.date.desc())
        .limit(1)
    )
    latest_price = result.scalar_one_or_none()

    return {
        "ticker": ticker,
        "company": company.name,
        "price": {
            "date": latest_price.date.isoformat() if latest_price else date.today().isoformat(),
            "close": latest_price.close if latest_price else None,
        },
        "metrics": {
            "pe_ratio": latest_metrics.pe_ratio,
            "pb_ratio": latest_metrics.pb_ratio,
            "roe": latest_metrics.roe,
            "eps": latest_metrics.eps,
            "book_value_per_share": latest_metrics.book_value_per_share,
            "dividend_yield": latest_metrics.dividend_yield,
            "dividend_per_share": latest_metrics.dividend_per_share,
        },
        "prices_saved": saved,
        "prices_updated": updated,
        "prices_total": len(df),
    }
