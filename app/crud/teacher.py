from typing import List, Optional
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session, selectinload
from app.models.teacher import Teacher
from app.models.enrollment import Enrollment
from app.schemas.teacher import TeacherCreate, TeacherUpdate


def create_teacher(db: Session, payload: TeacherCreate) -> Teacher:
    teacher = Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return get_teacher_by_id(db, teacher.id)  # Reload with relationships


def get_teacher_by_id(db: Session, teacher_id: int) -> Optional[Teacher]:
    stmt = (
        select(Teacher)
        .options(selectinload(Teacher.schedules))
        .where(Teacher.id == teacher_id)
    )
    teacher = db.scalar(stmt)
    if teacher:
        teacher.active_students_count = _count_active_students(db, teacher.id)
    return teacher


def search_teachers(
    db: Session,
    q: Optional[str] = None,
    active_only: bool = False,
) -> List[Teacher]:
    """
    Search teachers by name, phone, or subject (case-insensitive partial match),
    eager-loading their weekly schedule and active student count.
    """
    stmt = select(Teacher).options(selectinload(Teacher.schedules))

    if active_only:
        stmt = stmt.where(Teacher.is_active.is_(True))

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Teacher.full_name.ilike(pattern),
                Teacher.phone.ilike(pattern),
                func.array_to_string(Teacher.subjects, " ").ilike(pattern),
            )
        )

    stmt = stmt.order_by(Teacher.full_name.asc())
    teachers = list(db.scalars(stmt).all())

    # Batch-fetch active student counts in a single GROUP BY query (prevents N+1)
    if teachers:
        teacher_ids = [t.id for t in teachers]
        count_stmt = (
            select(Enrollment.teacher_id, func.count(func.distinct(Enrollment.student_id)))
            .where(
                Enrollment.teacher_id.in_(teacher_ids),
                Enrollment.is_active.is_(True),
            )
            .group_by(Enrollment.teacher_id)
        )
        counts_map = dict(db.execute(count_stmt).all())
        for t in teachers:
            t.active_students_count = counts_map.get(t.id, 0)

    return teachers


def update_teacher(
    db: Session, teacher: Teacher, payload: TeacherUpdate
) -> Teacher:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(teacher, field, value)
    db.commit()
    db.refresh(teacher)
    return get_teacher_by_id(db, teacher.id)


def _count_active_students(db: Session, teacher_id: int) -> int:
    stmt = select(func.count(func.distinct(Enrollment.student_id))).where(
        Enrollment.teacher_id == teacher_id,
        Enrollment.is_active.is_(True),
    )
    return db.scalar(stmt) or 0