from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.enrollment import EnrollmentCreateItem, EnrollmentUpdate


def validate_teacher_and_subject(
    db: Session, teacher_id: int, requested_subject: str
) -> tuple[Teacher, str]:
    """
    Verifies the teacher exists, is active, and teaches the requested subject.
    Returns (teacher, canonical_subject_name).
    """
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Teacher with ID {teacher_id} not found",
        )
    if not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Teacher '{teacher.full_name}' is currently inactive",
        )

    subject_clean = requested_subject.strip().lower()
    canonical_subject = next(
        (s for s in teacher.subjects if s.lower() == subject_clean), None
    )
    if not canonical_subject:
        allowed = ", ".join(teacher.subjects)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Teacher '{teacher.full_name}' does not teach '{requested_subject}'. "
                f"Available subjects: [{allowed}]"
            ),
        )
    return teacher, canonical_subject


def add_or_reactivate_enrollment(
    db: Session,
    student_id: int,
    item: EnrollmentCreateItem,
    commit: bool = True,
) -> Enrollment:
    """
    Enrolls a student under a teacher for a subject.
    If a dropped enrollment already exists, reactivates it instead of violating UniqueConstraint.
    """
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found",
        )

    teacher, canonical_subject = validate_teacher_and_subject(
        db, item.teacher_id, item.subject
    )
    agreed_fee = (
        item.monthly_fee
        if item.monthly_fee is not None
        else teacher.default_monthly_fee
    )

    existing = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.teacher_id == teacher.id,
            func.lower(Enrollment.subject) == canonical_subject.lower(),
        )
    )

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Student is already actively enrolled with '{teacher.full_name}' "
                    f"for '{canonical_subject}'."
                ),
            )
        # Reactivate previously dropped enrollment
        existing.is_active = True
        existing.monthly_fee = agreed_fee
        existing.enrolled_date = date.today()
        enrollment = existing
    else:
        enrollment = Enrollment(
            student_id=student_id,
            teacher_id=teacher.id,
            subject=canonical_subject,
            monthly_fee=agreed_fee,
            enrolled_date=date.today(),
            is_active=True,
        )
        db.add(enrollment)

    if commit:
        db.commit()
        return get_enrollment_by_id(db, enrollment.id)

    db.flush()
    return enrollment


def get_enrollment_by_id(db: Session, enrollment_id: int) -> Optional[Enrollment]:
    stmt = (
        select(Enrollment)
        .options(joinedload(Enrollment.teacher))
        .where(Enrollment.id == enrollment_id)
    )
    return db.scalar(stmt)


def update_enrollment(
    db: Session, enrollment: Enrollment, payload: EnrollmentUpdate
) -> Enrollment:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(enrollment, field, value)
    db.commit()
    return get_enrollment_by_id(db, enrollment.id)