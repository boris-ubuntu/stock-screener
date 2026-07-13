from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.smartlab_parser import SmartLabParser

router = APIRouter()


@router.post("/parse/smartlab/{ticker}")
async def parse_reports_from_smartlab(
        ticker: str,
        db: AsyncSession = Depends(get_db)
):
    """
    Парсит финансовые отчеты с Smart-Lab и сохраняет в БД
    """
    try:
        result = await SmartLabParser.parse_and_save(ticker, db)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка парсинга: {str(e)}"
        )


@router.get("/parse/smartlab/test/{ticker}")
async def test_parse_reports(
        ticker: str
):
    """
    Тестовый эндпоинт - показывает, какие данные будут загружены
    """
    try:
        reports = await SmartLabParser.parse_financial_reports(ticker)

        if not reports:
            return {
                "message": f"No reports found for {ticker}",
                "reports": []
            }

        return {
            "message": f"Found {len(reports)} reports for {ticker}",
            "ticker": ticker,
            "reports": reports
        }

    except Exception as e:
        return {
            "error": str(e)
        }