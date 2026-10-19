from datetime import date
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.teacher import Teacher
from app.schemas.student import StudentCreate, StudentUpdate
from app.crud.enrollment import add_or_reactivate_enrollment


def get_student_by_id(db: Session, student_id: int) -> Optional[Student]:
    stmt = (
        select(Student)
        .options(
            selectinload(Student.enrollments).joinedload(Enrollment.teacher)
        )
        .where(Student.id == student_id)
    )
    return db.scalar(stmt)


def create_student(db: Session, payload: StudentCreate) -> Student:
    """
    Atomically creates a Student and all initial Teacher Enrollments in a single transaction.
    If any teacher/subject validation fails, the entire transaction rolls back cleanly.
    """
    student_data = payload.model_dump(exclude={"enrollments"})
    if student_data.get("joined_date") is None:
        student_data["joined_date"] = date.today()

    student = Student(**student_data)
    db.add(student)
    db.flush()  # Generates student.id without committing yet

    for item in payload.enrollments:
        add_or_reactivate_enrollment(
            db=db,
            student_id=student.id,
            item=item,
            commit=False,
        )

    db.commit()
    return get_student_by_id(db, student.id)


def search_students(
    db: Session,
    q: Optional[str] = None,
    grade: Optional[str] = None,
    teacher_id: Optional[int] = None,
    active_only: bool = False,
) -> List[Student]:
    """
    Unified student search by student name, phone, guardian name/phone, subject, or teacher name.
    Eager-loads enrollments and teacher details in a single batch to prevent N+1 queries.
    """
    stmt = (
        select(Student)
        .options(
            selectinload(Student.enrollments).joinedload(Enrollment.teacher)
        )
        .distinct()
    )

    if active_only:
        stmt = stmt.where(Student.is_active.is_(True))

    if grade and grade.strip():
        stmt = stmt.where(Student.grade.ilike(f"%{grade.strip()}%"))

    if teacher_id is not None:
        stmt = stmt.join(Student.enrollments).where(
            Enrollment.teacher_id == teacher_id,
            Enrollment.is_active.is_(True),
        )

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = (
            stmt.outerjoin(Student.enrollments)
            .outerjoin(Enrollment.teacher)
            .where(
                or_(
                    Student.full_name.ilike(pattern),
                    Student.phone.ilike(pattern),
                    Student.guardian_name.ilike(pattern),
                    Student.guardian_phone.ilike(pattern),
                    Student.grade.ilike(pattern),
                    Enrollment.subject.ilike(pattern),
                    Teacher.full_name.ilike(pattern),
                )
            )
        )

    stmt = stmt.order_by(Student.full_name.asc())
    return list(db.scalars(stmt).all())


def update_student(
    db: Session, student: Student, payload: StudentUpdate
) -> Student:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)
    db.commit()
    return get_student_by_id(db, student.id)