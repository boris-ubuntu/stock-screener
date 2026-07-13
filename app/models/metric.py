from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    calculation_date = Column(Date, nullable=False)

    # Все поля могут быть NULL в БД
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    roe = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    book_value_per_share = Column(Float, nullable=True)
    dividend_per_share = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="metrics")

    def __repr__(self):
        return f"<Metric(company_id={self.company_id}, date={self.calculation_date})>"