from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.admin import Admin
from app.models.payment import Payment
from app.schemas.payment import (
    BatchPaymentCreate,
    BatchPaymentResponse,
    PaymentResponse,
    StudentMonthlyDuesSummary,
)
from app.crud import payment as crud_payment

router = APIRouter(prefix="/payments", tags=["Payments & Fee Ledger"])


@router.post(
    "/",
    response_model=BatchPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_student_payment(
    payload: BatchPaymentCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """
    Record monthly fee payments for one or more teacher enrollments under a single shared receipt.
    """
    return crud_payment.record_batch_payment(db, payload)


@router.get("/", response_model=List[PaymentResponse])
def list_payment_history(
    student_id: Optional[int] = Query(None, description="Filter by student ID"),
    teacher_id: Optional[int] = Query(None, description="Filter by teacher ID"),
    billing_month: Optional[str] = Query(
        None, description="Filter by billing month (YYYY-MM)"
    ),
    receipt_no: Optional[str] = Query(None, description="Search by receipt number"),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """Retrieve historical payment records and receipts."""
    return crud_payment.list_payments(
        db,
        student_id=student_id,
        teacher_id=teacher_id,
        billing_month=billing_month,
        receipt_no=receipt_no,
    )


@router.get(
    "/student/{student_id}/ledger",
    response_model=StudentMonthlyDuesSummary,
)
def get_student_fee_checklist(
    student_id: int,
    billing_month: str = Query(..., description="Billing month in YYYY-MM format"),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """
    Returns each active teacher enrollment for a student in the given billing month,
    showing which subjects are PAID vs UNPAID.
    """
    try:
        return crud_payment.get_student_monthly_ledger(db, student_id, billing_month)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get(
    "/dues",
    response_model=List[StudentMonthlyDuesSummary],
)
def get_monthly_dues_report(
    billing_month: str = Query(..., description="Billing month in YYYY-MM format"),
    payment_status: Optional[str] = Query(
        None,
        description="Filter by status: UNPAID, PARTIAL, or PAID",
    ),
    grade: Optional[str] = Query(None, description="Filter by student grade"),
    teacher_id: Optional[int] = Query(
        None, description="Filter dues for a specific teacher's subjects"
    ),
    q: Optional[str] = Query(None, description="Search by student name or phone"),
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """
    Center-wide monthly fee ledger showing expected, paid, and pending amounts per student.
    """
    try:
        return crud_payment.get_center_monthly_dues(
            db,
            billing_month=billing_month,
            status_filter=payment_status,
            grade=grade,
            teacher_id=teacher_id,
            q=q,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def void_payment_entry(
    payment_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """Deletes/voids an erroneously recorded payment entry."""
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found"
        )
    db.delete(payment)
    db.commit()