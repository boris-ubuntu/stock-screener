from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import matplotlib

matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import io
import numpy as np

from app.core.database import get_db
from app.models.company import Company
from app.models.stock_price import StockPrice

router = APIRouter()


def _build_candlestick_chart(ticker: str, prices_data: list) -> Figure:
    """Построить свечной график с MA50 (thread-safe, без plt)."""
    data = [
        {
            'date': p.date,
            'open': p.open,
            'high': p.high,
            'low': p.low,
            'close': p.close,
            'volume': p.volume,
        }
        for p in prices_data
    ]

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    df['MA50'] = df['close'].rolling(window=min(50, len(df))).mean()

    fig = Figure(figsize=(14, 8))
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)

    x = np.arange(len(df))
    width = 0.6

    for i, row in df.iterrows():
        color = 'green' if row['close'] >= row['open'] else 'red'
        rect = Rectangle(
            (i - width / 2, min(row['open'], row['close'])),
            width,
            abs(row['close'] - row['open']),
            facecolor=color,
            edgecolor=color,
            linewidth=1,
        )
        ax1.add_patch(rect)
        ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)

    ax1.plot(x, df['MA50'], color='blue', linewidth=2, label='MA50')
    ax1.set_title(f'{ticker} — Свечной график с MA50', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Цена (₽)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    colors = ['green' if row['close'] >= row['open'] else 'red' for _, row in df.iterrows()]
    ax2.bar(x, df['volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_xlabel('Дата', fontsize=12)
    ax2.set_ylabel('Объем', fontsize=12)
    ax2.grid(True, alpha=0.3)

    step = max(1, len(df) // 20)
    tick_positions = x[::step]
    tick_labels = [d.strftime('%Y-%m-%d') for d in df['date'][::step]]
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=45, ha='right')

    fig.tight_layout()
    return fig


@router.get("/chart/{ticker}")
async def get_chart(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Получить свечной график с MA50 для тикера (HTML-страница)."""
    result = await db.execute(select(Company).where(Company.ticker == ticker.upper()))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    result = await db.execute(
        select(StockPrice)
        .where(StockPrice.company_id == company.id)
        .order_by(StockPrice.date.asc())
    )
    prices = result.scalars().all()
    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

    fig = _build_candlestick_chart(ticker, prices)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    import base64
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    fig.clear()

    html = f"""<!DOCTYPE html>
<html>
<head><title>{ticker} — График</title></head>
<body style="background:#1a1a2e; text-align:center;">
  <h2 style="color:white;">{ticker}</h2>
  <img src="data:image/png;base64,{img_base64}" alt="Chart" style="max-width:100%;height:auto;">
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/chart-image/{ticker}")
async def get_chart_image(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Получить свечной график как изображение (PNG)."""
    result = await db.execute(select(Company).where(Company.ticker == ticker.upper()))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    result = await db.execute(
        select(StockPrice)
        .where(StockPrice.company_id == company.id)
        .order_by(StockPrice.date.asc())
    )
    prices = result.scalars().all()
    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

    fig = _build_candlestick_chart(ticker, prices)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    fig.clear()

    return StreamingResponse(buf, media_type="image/png")