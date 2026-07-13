from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class StockPriceCreate(BaseModel):
    company_id: int
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None


class StockPriceResponse(BaseModel):
    id: int
    company_id: int
    date: date
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True