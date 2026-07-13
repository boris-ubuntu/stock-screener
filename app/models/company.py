from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))

    revenue = Column(Float)  # Выручка
    net_income = Column(Float)  # Чистая прибыль
    total_debt = Column(Float)  # Общий долг
    total_assets = Column(Float)  # Активы

    reports = relationship("FinancialReport", back_populates="company", cascade="all, delete-orphan")
    prices = relationship("StockPrice", back_populates="company", cascade="all, delete-orphan")
    metrics = relationship("Metric", back_populates="company", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Company(ticker={self.ticker}, name={self.name})>"