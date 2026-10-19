from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.schedule import ScheduleResponse


class TeacherBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    subjects: List[str] = Field(..., min_length=1)
    default_monthly_fee: Decimal = Field(default=Decimal("500.00"), ge=0)
    is_active: bool = True

    @field_validator("subjects")
    @classmethod
    def clean_subjects(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("At least one valid subject is required")
        return cleaned


class TeacherCreate(TeacherBase):
    pass


class TeacherUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    subjects: Optional[List[str]] = None
    default_monthly_fee: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("subjects")
    @classmethod
    def clean_subjects(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("At least one valid subject is required")
        return cleaned


class TeacherResponse(TeacherBase):
    id: int
    created_at: datetime
    schedules: List[ScheduleResponse] = []
    active_students_count: int = 0

    model_config = {"from_attributes": True}