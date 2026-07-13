# 📊 Stock Screener

Скринер акций для анализа финансовых показателей компаний.

## 🚀 Что умеет:

- Загружать цены акций с биржи MOEX
- Рассчитывать мультипликаторы: P/E, P/B, ROE, EPS, Dividen Yield на основе csv МСФО
- Строить свечные графики с MA50

## 🛠️ Как запустить:

1. Установи Python 3.11+
2. Установи Docker Desktop
3. Открой терминал и выполни:

```bash
# Клонировать проект
git clone https://github.com/boris-ubuntu/stock-screener.git

# Перейти в папку
cd stock-screener

# Создать виртуальное окружение
python -m venv .venv

# Активировать (Windows)
.venv\Scripts\activate

# Установить библиотеки
pip install -r requirements.txt

# Запустить базу данных
docker-compose up -d

# Запустить сервер
uvicorn app.main:app --reload