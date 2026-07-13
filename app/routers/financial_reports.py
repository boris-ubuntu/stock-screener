from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.company import Company
from app.models.financial_report import FinancialReport
from app.schemas.financial_report import FinancialReportCreate, FinancialReportResponse

router = APIRouter()

@router.post("/financial-reports", response_model=FinancialReportResponse)
async def create_financial_report(
        report: FinancialReportCreate,
        db: AsyncSession = Depends(get_db)
):
    company = await db.get(Company, report.company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company with id {report.company_id} not found"
        )

    db_report = FinancialReport(**report.model_dump())
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)

    return db_report

@router.get("/financial-reports/company/{company_id}", response_model=List[FinancialReportResponse])
async def get_company_reports(
        company_id: int,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(FinancialReport)
        .where(FinancialReport.company_id == company_id)
        .order_by(FinancialReport.report_date.desc())
    )
    reports = result.scalars().all()
    return reports

@router.get("/financial-reports/{report_id}", response_model=FinancialReportResponse)
async def get_report_by_id(
        report_id: int,
        db: AsyncSession = Depends(get_db)
):
    report = await db.get(FinancialReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report