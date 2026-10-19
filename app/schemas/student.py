from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.schemas.enrollment import EnrollmentCreateItem, EnrollmentResponse


class StudentBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    guardian_name: str = Field(..., min_length=2, max_length=100)
    guardian_phone: str = Field(..., min_length=7, max_length=20)
    grade: str = Field(..., min_length=1, max_length=20)
    joined_date: Optional[date] = None
    is_active: bool = True


class StudentCreate(StudentBase):
    enrollments: List[EnrollmentCreateItem] = Field(
        default_factory=list,
        description="Initial teachers and subjects selected during onboarding",
    )

    @model_validator(mode="after")
    def check_duplicate_enrollments(self):
        seen = set()
        for item in self.enrollments:
            key = (item.teacher_id, item.subject.strip().lower())
            if key in seen:
                raise ValueError(
                    f"Duplicate enrollment in request: teacher_id={item.teacher_id}, subject='{item.subject}'"
                )
            seen.add(key)
        return self


class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    guardian_name: Optional[str] = Field(None, min_length=2, max_length=100)
    guardian_phone: Optional[str] = Field(None, min_length=7, max_length=20)
    grade: Optional[str] = Field(None, min_length=1, max_length=20)
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    id: int
    joined_date: date
    created_at: datetime
    enrollments: List[EnrollmentResponse] = []
    total_monthly_fee: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_total_active_fee(self):
        # Sum monthly_fee only for currently active enrollments
        self.total_monthly_fee = sum(
            (e.monthly_fee for e in self.enrollments if e.is_active),
            Decimal("0.00"),
        )
        return self