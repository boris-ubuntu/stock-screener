from pydantic import BaseModel
from datetime import date
from typing import Optional

class ReportCSVRow(BaseModel):
    """Структура одной строки CSV файла"""
    ticker: str
    report_date: date
    period_type: str  # 'quarter' или 'year'
    fiscal_year: int
    fiscal_quarter: Optional[int] = None
    revenue: float
    net_income: float
    total_debt: Optional[float] = None
    total_assets: Optional[float] = None
    equity: Optional[float] = None
    operating_income: Optional[float] = None
    ebitda: Optional[float] = None