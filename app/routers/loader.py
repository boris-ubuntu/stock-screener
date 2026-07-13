from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta
from app.core.database import get_db
from app.models.company import Company
from app.models.stock_price import StockPrice
from app.models.financial_report import FinancialReport
from app.services.moex_client import MOEXClient
from app.services.smartlab_parser import SmartLabParser
from app.services.metric_calculator import MetricCalculator
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/load-all/{ticker}")
async def load_all_data(
    ticker: str,
    days: int = 365,
    db: AsyncSession = Depends(get_db),
):
    """Загрузить все данные для компании: цены, отчеты, метрики"""
    result = await db.execute(select(Company).where(Company.ticker == ticker))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    report = {
        "ticker": ticker,
        "company": company.name,
        "prices": {"status": "skipped", "count": 0},
        "reports": {"status": "skipped", "count": 0},
        "metrics": {"status": "skipped"},
    }

    # 1. Загружаем цены
    try:
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        df = await MOEXClient.get_stock_prices(
            ticker=ticker,
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
        )
        if not df.empty:
            saved = 0
            for _, row in df.iterrows():
                existing = await db.execute(
                    select(StockPrice).where(
                        StockPrice.company_id == company.id,
                        StockPrice.date == row["date"],
                    )
                )
                if not existing.scalar_one_or_none():
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
            report["prices"] = {"status": "ok", "count": len(df), "saved": saved}
        else:
            report["prices"] = {"status": "no_data", "count": 0}
    except Exception as e:
        report["prices"] = {"status": "error", "error": str(e)}

    # 2. Загружаем отчеты со Smart-Lab
    try:
        reports_data = await SmartLabParser.parse_financial_reports(ticker)
        if reports_data:
            saved = 0
            for data in reports_data:
                existing = await db.execute(
                    select(FinancialReport).where(
                        FinancialReport.company_id == company.id,
                        FinancialReport.report_date == data["report_date"],
                        FinancialReport.period_type == data["period_type"],
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(
                        FinancialReport(
                            company_id=company.id,
                            report_date=data["report_date"],
                            period_type=data["period_type"],
                            fiscal_year=data["fiscal_year"],
                            fiscal_quarter=data.get("fiscal_quarter"),
                            revenue=data.get("revenue"),
                            net_income=data.get("net_income"),
                            total_debt=data.get("total_debt"),
                            total_assets=data.get("total_assets"),
                            equity=data.get("equity"),
                            operating_income=data.get("operating_income"),
                            ebitda=data.get("ebitda"),
                        )
                    )
                    saved += 1
            await db.commit()
            report["reports"] = {"status": "ok", "count": len(reports_data), "saved": saved}
        else:
            report["reports"] = {"status": "no_data", "count": 0}
    except Exception as e:
        report["reports"] = {"status": "error", "error": str(e)}

    # 3. Рассчитываем метрики
    try:
        metrics = await MetricCalculator.calculate_metrics(company.id, db)
        if metrics and "error" not in metrics:
            report["metrics"] = {"status": "ok", "pe_ratio": metrics.get("pe_ratio")}
        else:
            report["metrics"] = {"status": "no_data"}
    except Exception as e:
        report["metrics"] = {"status": "error", "error": str(e)}

    return report