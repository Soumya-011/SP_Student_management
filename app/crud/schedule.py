from datetime import time
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from app.models.schedule import Schedule
from app.models.teacher import Teacher
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, DAY_NAMES


def check_schedule_conflict(
    db: Session,
    teacher_id: int,
    day_of_week: int,
    start_time: time,
    end_time: time,
    exclude_schedule_id: Optional[int] = None,
) -> Optional[Schedule]:
    """
    Overlap condition: Existing.start_time < New.end_time AND Existing.end_time > New.start_time
    """
    stmt = select(Schedule).where(
        and_(
            Schedule.teacher_id == teacher_id,
            Schedule.day_of_week == day_of_week,
            Schedule.start_time < end_time,
            Schedule.end_time > start_time,
        )
    )
    if exclude_schedule_id is not None:
        stmt = stmt.where(Schedule.id != exclude_schedule_id)

    return db.scalar(stmt)


def create_schedule(db: Session, payload: ScheduleCreate) -> Schedule:
    teacher = db.get(Teacher, payload.teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher with ID {payload.teacher_id} not found",
        )

    conflict = check_schedule_conflict(
        db=db,
        teacher_id=payload.teacher_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    if conflict:
        day_str = DAY_NAMES[payload.day_of_week]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Schedule conflict on {day_str}: Teacher already has '{conflict.subject}' "
                f"({conflict.grade_batch}) from {conflict.start_time.strftime('%H:%M')} "
                f"to {conflict.end_time.strftime('%H:%M')}."
            ),
        )

    schedule = Schedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(
    db: Session, schedule: Schedule, payload: ScheduleUpdate
) -> Schedule:
    update_data = payload.model_dump(exclude_unset=True)

    new_day = update_data.get("day_of_week", schedule.day_of_week)
    new_start = update_data.get("start_time", schedule.start_time)
    new_end = update_data.get("end_time", schedule.end_time)

    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_time must be strictly after start_time",
        )

    conflict = check_schedule_conflict(
        db=db,
        teacher_id=schedule.teacher_id,
        day_of_week=new_day,
        start_time=new_start,
        end_time=new_end,
        exclude_schedule_id=schedule.id,
    )
    if conflict:
        day_str = DAY_NAMES[new_day]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Schedule conflict on {day_str}: Overlaps with '{conflict.subject}' "
                f"({conflict.grade_batch}) from {conflict.start_time.strftime('%H:%M')} "
                f"to {conflict.end_time.strftime('%H:%M')}."
            ),
        )

    for field, value in update_data.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


def get_schedules_by_teacher(db: Session, teacher_id: int) -> List[Schedule]:
    stmt = (
        select(Schedule)
        .where(Schedule.teacher_id == teacher_id)
        .order_by(Schedule.day_of_week.asc(), Schedule.start_time.asc())
    )
    return list(db.scalars(stmt).all())


def delete_schedule(db: Session, schedule: Schedule) -> None:
    db.delete(schedule)
    db.commit()