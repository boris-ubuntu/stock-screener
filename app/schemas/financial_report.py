from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class FinancialReportCreate(BaseModel):
    company_id: int
    report_date: date
    period_type: str  # 'quarter' или 'year'
    fiscal_year: int
    fiscal_quarter: Optional[int] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    total_debt: Optional[float] = None
    total_assets: Optional[float] = None
    equity: Optional[float] = None
    operating_income: Optional[float] = None
    ebitda: Optional[float] = None

class FinancialReportResponse(BaseModel):
    id: int
    company_id: int
    report_date: date
    period_type: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    revenue: Optional[float]
    net_income: Optional[float]
    total_debt: Optional[float]
    total_assets: Optional[float]
    equity: Optional[float]
    operating_income: Optional[float]
    ebitda: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True