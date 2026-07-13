from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.company import Company
from app.models.financial_report import FinancialReport
from app.services.csv_parser import CSVParser
from app.services.metric_calculator import MetricCalculator

router = APIRouter()


@router.post("/import/reports/csv")
async def import_reports_from_csv(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    """Загрузить финансовые отчеты из CSV файла"""

    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате CSV"
        )

    try:
        content = await file.read()
        records = CSVParser.parse_reports_csv(content)

        if not records:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пуст или не содержит данных"
            )

        saved_count = 0
        updated_count = 0
        errors = []

        for record in records:
            result = await db.execute(
                select(Company).where(Company.ticker == record['ticker'])
            )
            company = result.scalar_one_or_none()

            if not company:
                errors.append(f"Компания {record['ticker']} не найдена")
                continue

            existing = await db.execute(
                select(FinancialReport).where(
                    FinancialReport.company_id == company.id,
                    FinancialReport.report_date == record['report_date'],
                    FinancialReport.period_type == record['period_type']
                )
            )
            existing_report = existing.scalar_one_or_none()

            report_data = {
                'company_id': company.id,
                'report_date': record['report_date'],
                'period_type': record['period_type'],
                'fiscal_year': record.get('fiscal_year'),
                'fiscal_quarter': record.get('fiscal_quarter'),
                'revenue': record.get('revenue'),
                'net_income': record.get('net_income'),
                'total_debt': record.get('total_debt'),
                'total_assets': record.get('total_assets'),
                'equity': record.get('equity'),
                'operating_income': record.get('operating_income'),
                'ebitda': record.get('ebitda')
            }

            if existing_report:
                for key, value in report_data.items():
                    if key != 'company_id':
                        setattr(existing_report, key, value)
                updated_count += 1
            else:
                new_report = FinancialReport(**report_data)
                db.add(new_report)
                saved_count += 1

        await db.commit()

        # Пересчитываем метрики
        companies_result = await db.execute(select(Company))
        companies = companies_result.scalars().all()

        metrics_updated = 0
        for company in companies:
            try:
                await MetricCalculator.calculate_metrics(company.id, db)
                metrics_updated += 1
            except Exception as e:
                pass

        return {
            "message": f"Импорт завершен",
            "saved_new": saved_count,
            "updated_existing": updated_count,
            "errors": errors if errors else None,
            "metrics_updated": metrics_updated,
            "total_companies": len(companies)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")