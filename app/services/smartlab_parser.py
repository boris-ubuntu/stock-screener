import httpx
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, date
import logging
from typing import List, Dict, Any, Optional
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.financial_report import FinancialReport
from app.services.metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class SmartLabParser:
    """
    Парсер финансовых отчетов с Smart-Lab
    """

    BASE_URL = "https://smart-lab.ru/q/{ticker}/f/q/MSFO/"

    # Показатели, которые мы ищем на странице
    METRICS_MAP = {
        'чистая прибыль': 'net_income',
        'активы банка': 'total_assets',
        'капитал': 'equity',
        'опер. прибыль': 'operating_income',  # операционная прибыль (исправлено)
        'операционная прибыль': 'operating_income',
        'выручка': 'revenue',
        'долг': 'total_debt',
        'ebitda': 'ebitda',
    }

    @staticmethod
    async def parse_financial_reports(ticker: str) -> List[Dict[str, Any]]:
        """
        Парсит страницу с финансовыми отчетами на Smart-Lab
        """
        url = SmartLabParser.BASE_URL.format(ticker=ticker)

        logger.info(f"📊 Парсинг отчета для {ticker} с {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)

            if response.status_code != 200:
                logger.error(f"❌ Ошибка загрузки страницы: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Находим все строки таблицы
            rows = soup.find_all('tr')

            if not rows:
                logger.error(f"❌ Строки таблицы не найдены")
                return []

            # Извлекаем данные
            reports = SmartLabParser._extract_data_from_rows(ticker, rows)

            logger.info(f"✅ Загружено {len(reports)} отчетов для {ticker}")

            return reports

    @staticmethod
    def _extract_data_from_rows(ticker: str, rows) -> List[Dict[str, Any]]:
        """
        Извлекает данные из строк таблицы
        """
        # Сначала находим заголовки с датами
        dates = []
        for row in rows:
            cells = row.find_all(['th', 'td'])
            row_text = ' '.join([cell.get_text(strip=True) for cell in cells])

            # Ищем даты в формате DD.MM.YYYY или YYYYQN
            date_matches = re.findall(r'(\d{2}\.\d{2}\.\d{4})', row_text)
            if date_matches:
                for date_str in date_matches:
                    try:
                        d = datetime.strptime(date_str, '%d.%m.%Y').date()
                        if d not in dates:
                            dates.append(d)
                    except ValueError:
                        pass

            # Ищем даты в формате YYYYQN
            quarter_matches = re.findall(r'(\d{4})Q(\d)', row_text)
            if quarter_matches and not dates:
                for year, quarter in quarter_matches:
                    try:
                        month = int(quarter) * 3
                        d = datetime(int(year), month, 1).date()
                        if d not in dates:
                            dates.append(d)
                    except ValueError:
                        pass

        if not dates:
            logger.warning(f"❌ Даты не найдены")
            return []

        # Сортируем даты
        dates = sorted(dates)
        logger.info(f"📅 Найдены даты: {dates}")

        # Создаем структуру для отчетов
        reports = []
        for d in dates:
            # Определяем тип периода
            if d.month == 12 and d.day == 31:
                period_type = 'year'
                fiscal_quarter = None
            else:
                period_type = 'quarter'
                fiscal_quarter = (d.month - 1) // 3 + 1

            report = {
                'ticker': ticker,
                'report_date': d,
                'period_type': period_type,
                'fiscal_year': d.year,
                'fiscal_quarter': fiscal_quarter,
                'revenue': None,
                'net_income': None,
                'total_debt': None,
                'total_assets': None,
                'equity': None,
                'operating_income': None,
                'ebitda': None
            }
            reports.append(report)

        # Теперь ищем значения показателей
        for row in rows:
            cells = row.find_all(['th', 'td'])
            if len(cells) < 2:
                continue

            # Первая ячейка - название показателя
            indicator = cells[0].get_text(strip=True).lower()

            # Проверяем, есть ли этот показатель в нашей карте
            metric_type = None
            for key, value in SmartLabParser.METRICS_MAP.items():
                if key in indicator:
                    metric_type = value
                    break

            if not metric_type:
                continue

            logger.info(f"🔍 Найден показатель: {indicator} -> {metric_type}")

            # Извлекаем значения для каждой даты
            # Пропускаем первую ячейку (название) и ищем значения
            for i, cell in enumerate(cells[1:], 1):
                if i > len(dates):
                    break

                value_str = cell.get_text(strip=True)
                if value_str in ['?', '-', '']:
                    continue

                # Парсим число
                value = SmartLabParser._parse_number(value_str)
                if value is None:
                    continue

                # Сохраняем в соответствующий отчет
                report_date = dates[i - 1]
                for report in reports:
                    if report['report_date'] == report_date:
                        report[metric_type] = value
                        break

        # Фильтруем отчеты, где есть хоть какие-то данные
        filtered_reports = []
        for report in reports:
            if any(report.get(key) is not None for key in ['net_income', 'total_assets', 'equity']):
                filtered_reports.append(report)

        return filtered_reports

    @staticmethod
    def _parse_number(value_str: str) -> Optional[float]:
        """Парсит число из строки (с учетом млрд, млн, пробелов)"""
        if not value_str:
            return None

        # Убираем пробелы
        clean = value_str.replace(' ', '').replace(',', '.')

        # Проверяем наличие единиц измерения
        multiplier = 1
        if 'млрд' in clean:
            multiplier = 1_000_000_000
            clean = clean.replace('млрд', '')
        elif 'млн' in clean:
            multiplier = 1_000_000
            clean = clean.replace('млн', '')
        elif 'трлн' in clean:
            multiplier = 1_000_000_000_000
            clean = clean.replace('трлн', '')
        elif '%' in clean:
            # Проценты не преобразуем
            return None

        # Убираем все кроме цифр, точки и минуса
        clean = re.sub(r'[^0-9.\-]', '', clean)

        if not clean:
            return None

        try:
            value = float(clean) * multiplier
            return value
        except ValueError:
            return None

    @staticmethod
    async def parse_and_save(
            ticker: str,
            db: AsyncSession
    ) -> Dict[str, Any]:
        """Парсит отчеты и сохраняет в БД"""

        # Находим компанию
        result = await db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = result.scalar_one_or_none()

        if not company:
            return {"error": f"Company {ticker} not found"}

        # Парсим отчеты
        reports_data = await SmartLabParser.parse_financial_reports(ticker)

        if not reports_data:
            return {"error": f"No reports found for {ticker}"}

        # Сохраняем в БД
        saved = 0
        updated = 0

        for data in reports_data:
            existing = await db.execute(
                select(FinancialReport).where(
                    FinancialReport.company_id == company.id,
                    FinancialReport.report_date == data['report_date'],
                    FinancialReport.period_type == data['period_type']
                )
            )
            existing_report = existing.scalar_one_or_none()

            report_data = {
                'company_id': company.id,
                'report_date': data['report_date'],
                'period_type': data['period_type'],
                'fiscal_year': data['fiscal_year'],
                'fiscal_quarter': data['fiscal_quarter'],
                'revenue': data.get('revenue'),
                'net_income': data.get('net_income'),
                'total_debt': data.get('total_debt'),
                'total_assets': data.get('total_assets'),
                'equity': data.get('equity'),
                'operating_income': data.get('operating_income'),
                'ebitda': data.get('ebitda')
            }

            if existing_report:
                for key, value in report_data.items():
                    if key != 'company_id' and value is not None:
                        setattr(existing_report, key, value)
                updated += 1
            else:
                new_report = FinancialReport(**report_data)
                db.add(new_report)
                saved += 1

        await db.commit()

        # Пересчитываем метрики
        await MetricCalculator.calculate_metrics(company.id, db)

        return {
            "message": f"Parsed {len(reports_data)} reports for {ticker}",
            "saved_new": saved,
            "updated_existing": updated,
            "total": len(reports_data)
        }