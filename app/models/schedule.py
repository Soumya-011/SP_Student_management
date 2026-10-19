from datetime import time
from typing import Optional
from sqlalchemy import String, SmallInteger, Time, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Schedule(Base):
    """
    Fixed repeating weekly schedule for a teacher.
    day_of_week uses 0 = Monday, 1 = Tuesday, ..., 6 = Sunday for natural chronological sorting.
    """
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="ck_valid_day_of_week"),
        CheckConstraint("end_time > start_time", name="ck_valid_time_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, index=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_batch: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "Grade 9 - Batch A"
    room: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Relationships
    teacher: Mapped["Teacher"] = relationship("Teacher", back_populates="schedules")