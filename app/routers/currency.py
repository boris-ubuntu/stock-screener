from fastapi import APIRouter
from app.services.currency_service import CurrencyService

router = APIRouter()

@router.get("/currency/rates")
async def get_currency_rates():
    """
    Получить текущие курсы доллара и юаня
    """
    rates = await CurrencyService.get_rates()
    return rates