import httpx
import pandas as pd
from datetime import datetime, date, timedelta
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MOEXClient:
    BASE_URL = "https://iss.moex.com/iss"

    @staticmethod
    async def get_stock_prices(
            ticker: str,
            from_date: Optional[str] = None,
            to_date: Optional[str] = None,
            limit: int = 100
    ) -> pd.DataFrame:
        """Загрузить исторические цены с MOEX или последнюю цену"""

        if from_date is None:
            from_date = (date.today() - timedelta(days=365 * 3)).isoformat()
        if to_date is None:
            to_date = date.today().isoformat()

        boards = ["TQBR", "TQTF", "TQPD", "TQOB", "TQCB", "TQFB", "TQLV"]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for board in boards:
                url = f"{MOEXClient.BASE_URL}/history/engines/stock/markets/shares/boards/{board}/securities/{ticker}.json"

                all_data = []
                start = 0

                while True:
                    params = {
                        'from': from_date,
                        'till': to_date,
                        'limit': limit,
                        'start': start
                    }

                    try:
                        response = await client.get(url, params=params)
                        if response.status_code != 200:
                            break

                        data = response.json()
                        history = data.get('history', {})
                        rows = history.get('data', [])

                        if not rows:
                            break

                        columns = history.get('columns', [])
                        if 'TRADEDATE' not in columns or 'CLOSE' not in columns:
                            break

                        parsed_rows = MOEXClient._parse_rows(rows, columns)
                        all_data.extend(parsed_rows)

                        if len(rows) < limit:
                            break
                        start += limit

                    except Exception as e:
                        logger.debug(f"Ошибка при запросе {url}: {e}")
                        break

                if all_data:
                    df = pd.DataFrame(all_data)
                    df = df.sort_values('date')
                    logger.info(f"Загружено {len(df)} записей для {ticker} (борд {board})")
                    return df

            logger.info(f"Истории нет для {ticker}, пробую получить текущую цену...")
            current_price = await MOEXClient._get_marketdata_price(client, ticker)

            if current_price is not None:
                today = date.today()
                df = pd.DataFrame([{
                    'date': today,
                    'open': current_price,
                    'high': current_price,
                    'low': current_price,
                    'close': current_price,
                    'volume': 0
                }])
                logger.info(f"Добавлена цена {current_price} для {ticker}")
                return df

            logger.info(f"Пробую получить последнюю доступную цену из истории для {ticker}...")
            last_price = await MOEXClient._get_last_historical_price(client, ticker)

            if last_price is not None:
                today = date.today()
                df = pd.DataFrame([{
                    'date': today,
                    'open': last_price,
                    'high': last_price,
                    'low': last_price,
                    'close': last_price,
                    'volume': 0
                }])
                logger.info(f"Добавлена последняя цена {last_price} для {ticker}")
                return df

            logger.warning(f"Не удалось получить данные для {ticker}")
            return pd.DataFrame()

    @staticmethod
    async def _get_marketdata_price(client: httpx.AsyncClient, ticker: str) -> Optional[float]:
        """Получить последнюю цену из секции marketdata"""
        url = f"{MOEXClient.BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        params = {"iss.only": "marketdata"}

        try:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                return None

            data = response.json()
            marketdata = data.get('marketdata', {})
            columns = marketdata.get('columns', [])
            rows = marketdata.get('data', [])

            if not rows:
                logger.info("Нет активных торгов (рынок закрыт или бумага не торгуется)")
                return None

            price_idx = None
            for i, col in enumerate(columns):
                if col in ('LAST', 'CLOSEPRICE', 'CURRENTPRICE'):
                    price_idx = i
                    break

            if price_idx is None:
                return None

            row = rows[0]
            if price_idx < len(row):
                value = row[price_idx]
                if value is not None:
                    return float(value)
            return None

        except Exception as e:
            logger.error(f"Ошибка получения цены для {ticker}: {e}")
            return None

    @staticmethod
    async def _get_last_historical_price(client: httpx.AsyncClient, ticker: str) -> Optional[float]:
        """Получить последнюю доступную цену из истории"""
        from_date = (date.today() - timedelta(days=7)).isoformat()
        to_date = date.today().isoformat()

        boards = ["TQBR", "TQTF", "TQPD", "TQOB", "TQCB", "TQFB", "TQLV"]

        for board in boards:
            url = f"{MOEXClient.BASE_URL}/history/engines/stock/markets/shares/boards/{board}/securities/{ticker}.json"
            params = {
                'from': from_date,
                'till': to_date,
                'limit': 1,
                'start': 0
            }

            try:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    continue

                data = response.json()
                history = data.get('history', {})
                rows = history.get('data', [])

                if not rows:
                    continue

                columns = history.get('columns', [])
                if 'CLOSE' not in columns:
                    continue

                close_idx = columns.index('CLOSE')
                row = rows[0]
                if close_idx < len(row):
                    value = row[close_idx]
                    if value is not None:
                        logger.info(f"Найдена последняя цена из истории: {value}")
                        return float(value)

            except Exception as e:
                logger.debug(f"Ошибка получения последней цены для {ticker}: {e}")
                continue

        return None

    @staticmethod
    def _parse_rows(rows, columns):
        """Парсит строки данных в единый формат"""
        result = []
        col_map = {
            'TRADEDATE': 'date', 'DATE': 'date', 'TRADE_DATE': 'date',
            'OPEN': 'open', 'PRICE_OPEN': 'open',
            'HIGH': 'high', 'PRICE_HIGH': 'high',
            'LOW': 'low', 'PRICE_LOW': 'low',
            'CLOSE': 'close', 'PRICE_CLOSE': 'close', 'LAST': 'close',
            'VOLUME': 'volume', 'VALUE': 'volume'
        }

        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                if col in col_map:
                    val = row[i]
                    field = col_map[col]
                    if field == 'date':
                        if isinstance(val, str):
                            try:
                                val = datetime.strptime(val, '%Y-%m-%d').date()
                            except Exception:
                                try:
                                    val = datetime.strptime(val, '%d.%m.%Y').date()
                                except Exception:
                                    continue
                        elif isinstance(val, (int, float)):
                            val = datetime.fromtimestamp(val / 1000).date()
                    else:
                        try:
                            val = float(val) if val is not None else None
                        except Exception:
                            val = None
                    record[field] = val
            if record.get('date') and record.get('close') is not None:
                result.append(record)
        return result
