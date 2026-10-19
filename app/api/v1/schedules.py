from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.crud import schedule as crud_schedule

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def add_schedule_slot(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_schedule.create_schedule(db, payload)


@router.get("/teacher/{teacher_id}", response_model=List[ScheduleResponse])
def get_teacher_timetable(
    teacher_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_schedule.get_schedules_by_teacher(db, teacher_id)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def edit_schedule_slot(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule slot not found"
        )
    return crud_schedule.update_schedule(db, schedule, payload)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_schedule_slot(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule slot not found"
        )
    crud_schedule.delete_schedule(db, schedule)