import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CurrencyService:
    """Сервис для получения курсов валют"""

    # API Центрального Банка России
    CBR_API = "https://www.cbr-xml-daily.ru/daily_json.js"

    @staticmethod
    async def get_rates() -> Dict[str, Any]:
        """
        Получить текущие курсы доллара и юаня
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(CurrencyService.CBR_API)
                response.raise_for_status()

                data = response.json()
                rates = data.get("Valute", {})

                usd_rate = rates.get("USD", {}).get("Value")
                cny_rate = rates.get("CNY", {}).get("Value")

                return {
                    "usd": usd_rate,
                    "cny": cny_rate,
                    "updated_at": data.get("Date")
                }

        except Exception as e:
            logger.error(f"Ошибка получения курсов валют: {e}")
            return {
                "usd": None,
                "cny": None,
                "updated_at": None,
                "error": str(e)
            }