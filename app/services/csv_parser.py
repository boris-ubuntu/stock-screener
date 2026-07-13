import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
import logging
import io

logger = logging.getLogger(__name__)


class CSVParser:
    """Парсер финансовых отчетов из CSV файлов"""

    @staticmethod
    def parse_reports_csv(file_content: bytes) -> List[Dict[str, Any]]:
        """Парсит CSV файл с финансовыми отчетами"""
        try:
            # Читаем CSV из байтов
            df = pd.read_csv(io.BytesIO(file_content))

            # Проверяем наличие обязательных колонок
            required_cols = ['ticker', 'report_date', 'period_type', 'fiscal_year']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(f"Отсутствуют обязательные колонки: {missing_cols}")

            # Преобразуем даты
            df['report_date'] = pd.to_datetime(df['report_date']).dt.date

            # Заменяем NaN на None
            df = df.replace({np.nan: None, '': None, 'NA': None, 'NaN': None})
            df = df.where(pd.notnull(df), None)

            # Преобразуем в список словарей
            records = df.to_dict('records')

            logger.info(f"Загружено {len(records)} записей из CSV")

            return records

        except Exception as e:
            logger.error(f"Ошибка парсинга CSV: {e}")
            raise ValueError(f"Неверный формат CSV файла: {e}")