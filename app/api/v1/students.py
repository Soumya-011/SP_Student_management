from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.schemas.enrollment import (
    EnrollmentCreateItem,
    EnrollmentUpdate,
    EnrollmentResponse,
)
from app.crud import student as crud_student
from app.crud import enrollment as crud_enrollment

router = APIRouter(prefix="/students", tags=["Students & Enrollments"])


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def register_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_student.create_student(db, payload)


@router.get("/", response_model=List[StudentResponse])
def list_or_search_students(
    q: Optional[str] = Query(
        None,
        description="Search by student name, phone, guardian, grade, subject, or teacher name",
    ),
    grade: Optional[str] = Query(None, description="Filter by student grade"),
    teacher_id: Optional[int] = Query(
        None, description="Filter students actively attending a specific teacher"
    ),
    active_only: bool = Query(False, description="Only return active students"),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_student.search_students(
        db, q=q, grade=grade, teacher_id=teacher_id, active_only=active_only
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_details(
    student_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    student = crud_student.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_profile(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    student = crud_student.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )
    return crud_student.update_student(db, student, payload)


# --- Dynamic Multi-Teacher Enrollment Endpoints ---


@router.post(
    "/{student_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_teacher_enrollment(
    student_id: int,
    payload: EnrollmentCreateItem,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """Add a new teacher/subject to an existing student (or reactivate a previously dropped one)."""
    return crud_enrollment.add_or_reactivate_enrollment(
        db, student_id=student_id, item=payload, commit=True
    )


@router.patch(
    "/{student_id}/enrollments/{enrollment_id}",
    response_model=EnrollmentResponse,
)
def modify_or_drop_enrollment(
    student_id: int,
    enrollment_id: int,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """Change the agreed monthly fee or drop/reactivate an enrollment (is_active: false/true)."""
    enrollment = crud_enrollment.get_enrollment_by_id(db, enrollment_id)
    if not enrollment or enrollment.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found for this student",
        )
    return crud_enrollment.update_enrollment(db, enrollment, payload)