from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, Boolean, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    subjects: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    default_monthly_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("500.00")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    enrollments: Mapped[List["Enrollment"]] = relationship(
        "Enrollment", back_populates="teacher", cascade="all, delete-orphan"
    )
    schedules: Mapped[List["Schedule"]] = relationship(
        "Schedule",
        back_populates="teacher",
        cascade="all, delete-orphan",
        order_by="Schedule.day_of_week, Schedule.start_time",
    )