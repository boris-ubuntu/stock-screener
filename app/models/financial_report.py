from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_date = Column(Date, nullable=False)  # Дата отчета (квартал/год)
    period_type = Column(String(10), nullable=False)  # 'quarter' или 'year'
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer)  # 1,2,3,4 для квартальных
    revenue = Column(Float)  # Выручка
    net_income = Column(Float)  # Чистая прибыль
    total_debt = Column(Float)  # Общий долг
    total_assets = Column(Float)  # Активы
    equity = Column(Float)  # Собственный капитал
    operating_income = Column(Float)  # Операционная прибыль
    ebitda = Column(Float)  # EBITDA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    company = relationship("Company", back_populates="reports")

    def __repr__(self):
        return f"<FinancialReport(company_id={self.company_id}, date={self.report_date})>"