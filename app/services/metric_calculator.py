from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
import logging
from typing import Optional, Dict, Any

from app.models.company import Company
from app.models.financial_report import FinancialReport
from app.models.stock_price import StockPrice
from app.models.metric import Metric

logger = logging.getLogger(__name__)


class MetricCalculator:
    """Калькулятор финансовых мультипликаторов"""

    DIVIDEND_REFERENCE = {
        'SBER': 37.64,
        'CNRU': 53.0,
        'YDEX': 190.0,
        'DIAS': 120.0,   # Дивиденд 120 ₽ на акцию
        'NMTP': 1.1448,
        'MDMG': 89.0,
        'BELU': 30.0,
        'RENI': 10.0,
        'MOEX': 19.57,
        'X5': 613.0,
    }

    SHARES_OUTSTANDING_MILLIONS = {
        'SBER': 21587.0,
        'CNRU': 75.0,
        'YDEX': 390.0,
        'DIAS': 10.5,    # 10.5 млн акций
        'NMTP': 19260.0,
        'MDMG': 75.1,
        'BELU': 126.4,
        'RENI': 557.0,
        'MOEX': 2276.0,
        'X5': 271.6,
    }

    @staticmethod
    async def calculate_metrics(
            company_id: int,
            db: AsyncSession
    ) -> Dict[str, Any]:
        """Рассчитать мультипликаторы для компании"""

        company = await db.get(Company, company_id)
        if not company:
            return {"error": "Company not found"}

        result = await db.execute(
            select(FinancialReport)
            .where(FinancialReport.company_id == company_id)
            .order_by(FinancialReport.report_date.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()

        if not report:
            return {"error": "No financial reports found"}

        result = await db.execute(
            select(StockPrice)
            .where(StockPrice.company_id == company_id)
            .order_by(StockPrice.date.desc())
            .limit(1)
        )
        price = result.scalar_one_or_none()

        if not price:
            return {"error": "No price data found"}

        metrics = {}

        shares_millions = MetricCalculator.SHARES_OUTSTANDING_MILLIONS.get(company.ticker, 0)
        if shares_millions == 0:
            logger.warning(f"Неизвестное количество акций для {company.ticker}")
            shares_millions = 1

        price_close = price.close if price.close is not None else None

        # --- Приводим данные к единому формату (млн руб) ---
        net_income = float(report.net_income) if report.net_income is not None else None
        equity = float(report.equity) if report.equity is not None else None
        total_debt = float(report.total_debt) if report.total_debt is not None else None

        # --- EPS (Прибыль на акцию) ---
        if net_income is not None:
            try:
                eps = net_income / shares_millions
                metrics['eps'] = eps
            except (ValueError, TypeError):
                metrics['eps'] = None
        else:
            metrics['eps'] = None

        # --- Book Value per Share ---
        if equity is not None:
            try:
                book_value = equity / shares_millions
                metrics['book_value_per_share'] = book_value
            except (ValueError, TypeError):
                metrics['book_value_per_share'] = None
        else:
            metrics['book_value_per_share'] = None

        # --- P/E ---
        if price_close is not None and metrics.get('eps') and metrics['eps'] > 0:
            metrics['pe_ratio'] = price_close / metrics['eps']
        else:
            metrics['pe_ratio'] = None

        # --- P/B ---
        if price_close is not None and metrics.get('book_value_per_share') and metrics['book_value_per_share'] > 0:
            metrics['pb_ratio'] = price_close / metrics['book_value_per_share']
        else:
            metrics['pb_ratio'] = None

        # --- ROE ---
        if equity and equity > 0 and net_income:
            try:
                metrics['roe'] = (net_income / equity) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                metrics['roe'] = None
        else:
            metrics['roe'] = None

        # --- Debt/Equity ---
        if equity and equity > 0 and total_debt:
            try:
                metrics['debt_to_equity'] = total_debt / equity
            except (ValueError, TypeError, ZeroDivisionError):
                metrics['debt_to_equity'] = None
        else:
            metrics['debt_to_equity'] = None

        # --- Дивиденды ---
        dividend_per_share = MetricCalculator.DIVIDEND_REFERENCE.get(company.ticker, 0.0)
        metrics['dividend_per_share'] = dividend_per_share

        if dividend_per_share > 0 and price_close is not None and price_close > 0:
            metrics['dividend_yield'] = (dividend_per_share / price_close) * 100
        else:
            metrics['dividend_yield'] = None

        # --- Сохраняем в БД ---
        db_metric = Metric(
            company_id=company_id,
            calculation_date=date.today(),
            pe_ratio=metrics.get('pe_ratio'),
            pb_ratio=metrics.get('pb_ratio'),
            roe=metrics.get('roe'),
            debt_to_equity=metrics.get('debt_to_equity'),
            eps=metrics.get('eps'),
            book_value_per_share=metrics.get('book_value_per_share'),
            dividend_per_share=metrics.get('dividend_per_share'),
            dividend_yield=metrics.get('dividend_yield')
        )

        db.add(db_metric)
        await db.commit()

        return metrics

    @staticmethod
    async def get_latest_metrics(
            company_id: int,
            db: AsyncSession
    ) -> Optional[Metric]:
        """Получить последние рассчитанные метрики"""
        result = await db.execute(
            select(Metric)
            .where(Metric.company_id == company_id)
            .order_by(Metric.calculation_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()