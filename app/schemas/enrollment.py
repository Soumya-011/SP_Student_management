from datetime import date
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class EnrollmentCreateItem(BaseModel):
    """Used when enrolling a student with one or more teachers."""
    teacher_id: int
    subject: str = Field(..., min_length=1, max_length=50)
    monthly_fee: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Leave null to auto-fill from the teacher's default_monthly_fee",
    )


class EnrollmentUpdate(BaseModel):
    """Used to adjust a student's fee for a specific subject or drop/reactivate the teacher."""
    monthly_fee: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    teacher_id: int
    teacher_name: str = ""
    teacher_phone: str = ""
    subject: str
    monthly_fee: Decimal
    enrolled_date: date
    is_active: bool

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_teacher_details(cls, data: Any) -> Any:
        # Automatically flatten teacher name & phone when serializing SQLAlchemy Enrollment objects
        if hasattr(data, "teacher") and data.teacher is not None:
            return {
                "id": data.id,
                "student_id": data.student_id,
                "teacher_id": data.teacher_id,
                "teacher_name": data.teacher.full_name,
                "teacher_phone": data.teacher.phone,
                "subject": data.subject,
                "monthly_fee": data.monthly_fee,
                "enrolled_date": data.enrolled_date,
                "is_active": data.is_active,
            }
        return data