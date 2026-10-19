from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.admin import Admin
from app.models.student import Student
from app.models.teacher import Teacher
from app.crud.payment import get_center_monthly_dues

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

web_router = APIRouter(tags=["Web UI"])


def get_optional_admin(request: Request, db: Session) -> Optional[Admin]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.scalar(select(Admin).where(Admin.username == username))


@web_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if get_optional_admin(request, db):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={})


@web_router.get("/", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    admin = get_optional_admin(request, db)
    if not admin:
        return RedirectResponse(url="/login", status_code=302)

    current_month = date.today().strftime("%Y-%m")
    active_students = (
        db.scalar(
            select(func.count(Student.id)).where(Student.is_active.is_(True))
        )
        or 0
    )
    active_teachers = (
        db.scalar(
            select(func.count(Teacher.id)).where(Teacher.is_active.is_(True))
        )
        or 0
    )

    dues_list = get_center_monthly_dues(db, billing_month=current_month)
    month_expected = sum((d.total_expected_fee for d in dues_list), Decimal("0.00"))
    month_collected = sum((d.total_paid for d in dues_list), Decimal("0.00"))
    month_pending = sum((d.total_pending for d in dues_list), Decimal("0.00"))
    unpaid_students_count = sum(
        1 for d in dues_list if d.payment_status in ("UNPAID", "PARTIAL")
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "admin": admin,
            "active_page": "dashboard",
            "current_month": current_month,
            "stats": {
                "active_students": active_students,
                "active_teachers": active_teachers,
                "month_expected": month_expected,
                "month_collected": month_collected,
                "month_pending": month_pending,
                "unpaid_students_count": unpaid_students_count,
            },
        },
    )


@web_router.get("/students", response_class=HTMLResponse)
def students_page(request: Request, db: Session = Depends(get_db)):
    admin = get_optional_admin(request, db)
    if not admin:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={"admin": admin, "active_page": "students"},
    )


@web_router.get("/teachers", response_class=HTMLResponse)
def teachers_page(request: Request, db: Session = Depends(get_db)):
    admin = get_optional_admin(request, db)
    if not admin:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="teachers.html",
        context={"admin": admin, "active_page": "teachers"},
    )


@web_router.get("/payments", response_class=HTMLResponse)
def payments_page(request: Request, db: Session = Depends(get_db)):
    admin = get_optional_admin(request, db)
    if not admin:
        return RedirectResponse(url="/login", status_code=302)
    current_month = date.today().strftime("%Y-%m")
    return templates.TemplateResponse(
        request=request,
        name="payments.html",
        context={
            "admin": admin,
            "active_page": "payments",
            "current_month": current_month,
        },
    )