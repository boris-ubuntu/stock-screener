from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.core.database import get_db
from app.models.company import Company

router = APIRouter()

class CompanyCreate(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None

class CompanyResponse(BaseModel):
    id: int
    ticker: str
    name: str
    sector: Optional[str]
    industry: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CompanyUpdate(BaseModel):
    ticker: Optional[str] = None
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

@router.post("/companies", response_model=CompanyResponse)
async def create_company(
        company: CompanyCreate,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Company).where(Company.ticker == company.ticker)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Company with ticker {company.ticker} already exists"
        )
    db_company = Company(
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        industry=company.industry
    )
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    return db_company

@router.get("/companies", response_model=list[CompanyResponse])
async def get_companies(
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company))
    companies = result.scalars().all()
    return companies

@router.get("/companies/{ticker}", response_model=CompanyResponse)
async def get_company_by_ticker(
        ticker: str,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Company).where(Company.ticker == ticker)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ticker {ticker} not found"
        )
    return company


@router.put("/companies/{ticker}", response_model=CompanyResponse)
async def update_company(
    ticker: str,
    update: CompanyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить данные компании по тикеру"""
    result = await db.execute(
        select(Company).where(Company.ticker == ticker)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company with ticker {ticker} not found"
        )

    if update.ticker is not None:
        # Проверяем, что новый тикер не занят
        existing = await db.execute(
            select(Company).where(Company.ticker == update.ticker)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Company with ticker {update.ticker} already exists"
            )
        company.ticker = update.ticker
    if update.name is not None:
        company.name = update.name
    if update.sector is not None:
        company.sector = update.sector
    if update.industry is not None:
        company.industry = update.industry

    await db.commit()
    await db.refresh(company)
    return company
