from datetime import date
from decimal import Decimal
from typing import List
from sqlalchemy import String, Boolean, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Enrollment(Base):
    """
    Junction table connecting Students and Teachers per Subject,
    storing the agreed monthly fee for that specific teacher/subject.
    """
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "teacher_id", "subject", name="uq_student_teacher_subject"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    enrolled_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="enrollments")
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="enrollments")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="enrollment")