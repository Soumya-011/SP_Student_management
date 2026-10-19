from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Payment(Base):
    """
    Records a monthly fee payment for a specific student enrollment (teacher + subject).
    """
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "billing_month", name="uq_enrollment_billing_month"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    billing_month: Mapped[str] = mapped_column(
        String(7), index=True, nullable=False
    )  # Format: "YYYY-MM" (e.g., "2026-10")
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(30), default="Cash", nullable=False
    )  # e.g., Cash, UPI, Bank Transfer
    receipt_no: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="payments")
    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="payments")