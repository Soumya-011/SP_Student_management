from datetime import time
from typing import Optional
from pydantic import BaseModel, Field, model_validator

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class ScheduleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday through 6=Sunday")
    start_time: time
    end_time: time
    subject: str = Field(..., min_length=1, max_length=50)
    grade_batch: str = Field(..., min_length=1, max_length=50)
    room: Optional[str] = Field(None, max_length=30)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be strictly after start_time")
        return self


class ScheduleCreate(ScheduleBase):
    teacher_id: int


class ScheduleUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=50)
    grade_batch: Optional[str] = Field(None, min_length=1, max_length=50)
    room: Optional[str] = Field(None, max_length=30)


class ScheduleResponse(ScheduleBase):
    id: int
    teacher_id: int
    day_name: str = ""

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def populate_day_name(self):
        self.day_name = DAY_NAMES[self.day_of_week]
        return self