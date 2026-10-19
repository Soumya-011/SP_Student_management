from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), index=True, nullable=True)
    guardian_name: Mapped[str] = mapped_column(String(100), nullable=False)
    guardian_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    joined_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="student", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="student", cascade="all, delete-orphan"
    )