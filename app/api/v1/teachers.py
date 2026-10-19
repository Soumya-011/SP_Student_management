from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse
from app.crud import teacher as crud_teacher

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.post("/", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_new_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_teacher.create_teacher(db, payload)


@router.get("/", response_model=List[TeacherResponse])
def list_or_search_teachers(
    q: Optional[str] = Query(
        None, description="Search by teacher name, phone, or subject"
    ),
    active_only: bool = Query(False, description="Filter only active teachers"),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    return crud_teacher.search_teachers(db, q=q, active_only=active_only)


@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    teacher = crud_teacher.get_teacher_by_id(db, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return teacher


@router.patch("/{teacher_id}", response_model=TeacherResponse)
def update_existing_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    teacher = crud_teacher.get_teacher_by_id(db, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found"
        )
    return crud_teacher.update_teacher(db, teacher, payload)