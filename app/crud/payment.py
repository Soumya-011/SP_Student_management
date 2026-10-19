import calendar
import secrets
from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.payment import Payment
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.schemas.payment import (
    BatchPaymentCreate,
    BatchPaymentResponse,
    PaymentResponse,
    EnrollmentFeeStatus,
    StudentMonthlyDuesSummary,
    validate_YYYY_MM,
)


def _generate_receipt_no(billing_month: str) -> str:
    """Generates a collision-resistant receipt code like RCP-202610-4F9A1C."""
    month_compact = billing_month.replace("-", "")
    token = secrets.token_hex(3).upper()
    return f"RCP-{month_compact}-{token}"


def _last_day_of_billing_month(billing_month: str) -> date:
    """Returns the last calendar date of a 'YYYY-MM' string (e.g., 2026-10 -> 2026-10-31)."""
    year, month = map(int, billing_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def record_batch_payment(
    db: Session, payload: BatchPaymentCreate
) -> BatchPaymentResponse:
    """
    Atomically records payments for one or more teacher enrollments for a student,
    assigning a single shared receipt_no.
    """
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {payload.student_id} not found",
        )

    receipt_no = _generate_receipt_no(payload.billing_month)
    pay_date = payload.payment_date or date.today()
    created_payments: List[Payment] = []

    for item in payload.items:
        enrollment = db.scalar(
            select(Enrollment)
            .options(joinedload(Enrollment.teacher))
            .where(Enrollment.id == item.enrollment_id)
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Enrollment ID {item.enrollment_id} not found",
            )
        if enrollment.student_id != student.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Enrollment ID {item.enrollment_id} does not belong to "
                    f"student '{student.full_name}' (ID {student.id})"
                ),
            )

        # Check if already paid for this billing_month
        existing_payment = db.scalar(
            select(Payment).where(
                Payment.enrollment_id == enrollment.id,
                Payment.billing_month == payload.billing_month,
            )
        )
        if existing_payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Fee for '{enrollment.subject}' ({enrollment.teacher.full_name}) "
                    f"is already paid for {payload.billing_month} "
                    f"(Receipt: {existing_payment.receipt_no})."
                ),
            )

        amount = (
            item.amount_paid
            if item.amount_paid is not None
            else enrollment.monthly_fee
        )

        payment = Payment(
            student_id=student.id,
            enrollment_id=enrollment.id,
            billing_month=payload.billing_month,
            amount_paid=amount,
            payment_date=pay_date,
            payment_method=payload.payment_method.strip(),
            receipt_no=receipt_no,
            notes=payload.notes,
        )
        db.add(payment)
        created_payments.append(payment)

    db.commit()

    # Reload with relationships for response serialization
    payment_ids = [p.id for p in created_payments]
    reloaded_payments = list(
        db.scalars(
            select(Payment)
            .options(
                joinedload(Payment.student),
                joinedload(Payment.enrollment).joinedload(Enrollment.teacher),
            )
            .where(Payment.id.in_(payment_ids))
            .order_by(Payment.id.asc())
        ).all()
    )

    serialized = [PaymentResponse.model_validate(p) for p in reloaded_payments]
    total_paid = sum((p.amount_paid for p in serialized), Decimal("0.00"))

    return BatchPaymentResponse(
        receipt_no=receipt_no,
        student_id=student.id,
        student_name=student.full_name,
        billing_month=payload.billing_month,
        payment_date=pay_date,
        payment_method=payload.payment_method,
        total_amount_paid=total_paid,
        payments=serialized,
    )


def list_payments(
    db: Session,
    student_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    billing_month: Optional[str] = None,
    receipt_no: Optional[str] = None,
) -> List[Payment]:
    """Search and filter historical payment records."""
    stmt = select(Payment).options(
        joinedload(Payment.student),
        joinedload(Payment.enrollment).joinedload(Enrollment.teacher),
    )

    if student_id is not None:
        stmt = stmt.where(Payment.student_id == student_id)

    if teacher_id is not None:
        stmt = stmt.join(Payment.enrollment).where(Enrollment.teacher_id == teacher_id)

    if billing_month and billing_month.strip():
        validated_month = validate_YYYY_MM(billing_month)
        stmt = stmt.where(Payment.billing_month == validated_month)

    if receipt_no and receipt_no.strip():
        stmt = stmt.where(Payment.receipt_no.ilike(f"%{receipt_no.strip()}%"))

    stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())
    return list(db.scalars(stmt).all())


def _build_student_dues_summary(
    student: Student,
    billing_month: str,
    cutoff_date: date,
    payments_by_enrollment: dict[int, Payment],
    teacher_id_filter: Optional[int] = None,
) -> StudentMonthlyDuesSummary:
    """
    Computes per-subject and total monthly dues for a student in a specific billing month.
    Includes active enrollments that started on or before the end of that billing month,
    PLUS any dropped enrollment that already has a recorded payment in that month.
    """
    enrollment_statuses: List[EnrollmentFeeStatus] = []
    total_expected = Decimal("0.00")
    total_paid = Decimal("0.00")

    for enrollment in student.enrollments:
        if teacher_id_filter is not None and enrollment.teacher_id != teacher_id_filter:
            continue

        payment = payments_by_enrollment.get(enrollment.id)

        # Skip enrollments created after the billing month unless already paid
        if enrollment.enrolled_date > cutoff_date and not payment:
            continue

        # Skip inactive enrollments unless a historical payment exists for that month
        if not enrollment.is_active and not payment:
            continue

        is_paid = payment is not None
        paid_amt = payment.amount_paid if payment else Decimal("0.00")

        total_expected += enrollment.monthly_fee
        total_paid += paid_amt

        enrollment_statuses.append(
            EnrollmentFeeStatus(
                enrollment_id=enrollment.id,
                teacher_id=enrollment.teacher_id,
                teacher_name=enrollment.teacher.full_name if enrollment.teacher else "",
                subject=enrollment.subject,
                monthly_fee=enrollment.monthly_fee,
                is_paid=is_paid,
                amount_paid=paid_amt,
                payment_id=payment.id if payment else None,
                receipt_no=payment.receipt_no if payment else None,
                payment_date=payment.payment_date if payment else None,
                payment_method=payment.payment_method if payment else None,
            )
        )

    total_pending = max(Decimal("0.00"), total_expected - total_paid)

    if not enrollment_statuses:
        status_label = "NO_ACTIVE_ENROLLMENTS"
    elif total_paid == Decimal("0.00"):
        status_label = "UNPAID"
    elif total_paid >= total_expected or all(e.is_paid for e in enrollment_statuses):
        status_label = "PAID"
    else:
        status_label = "PARTIAL"

    return StudentMonthlyDuesSummary(
        student_id=student.id,
        student_name=student.full_name,
        phone=student.phone,
        guardian_name=student.guardian_name,
        guardian_phone=student.guardian_phone,
        grade=student.grade,
        billing_month=billing_month,
        total_expected_fee=total_expected,
        total_paid=total_paid,
        total_pending=total_pending,
        payment_status=status_label,
        enrollments=enrollment_statuses,
    )


def get_student_monthly_ledger(
    db: Session, student_id: int, billing_month: str
) -> StudentMonthlyDuesSummary:
    """Returns the exact paid/unpaid breakdown for a single student in a given YYYY-MM."""
    validated_month = validate_YYYY_MM(billing_month)
    cutoff_date = _last_day_of_billing_month(validated_month)

    student = db.scalar(
        select(Student)
        .options(selectinload(Student.enrollments).joinedload(Enrollment.teacher))
        .where(Student.id == student_id)
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.student_id == student_id,
                Payment.billing_month == validated_month,
            )
        ).all()
    )
    payments_map = {p.enrollment_id: p for p in payments}

    return _build_student_dues_summary(
        student=student,
        billing_month=validated_month,
        cutoff_date=cutoff_date,
        payments_by_enrollment=payments_map,
    )


def get_center_monthly_dues(
    db: Session,
    billing_month: str,
    status_filter: Optional[str] = None,
    grade: Optional[str] = None,
    teacher_id: Optional[int] = None,
    q: Optional[str] = None,
) -> List[StudentMonthlyDuesSummary]:
    """
    Generates the coaching center's monthly fee ledger across all active students
    in 2 batch SQL queries (0 N+1 queries).
    """
    validated_month = validate_YYYY_MM(billing_month)
    cutoff_date = _last_day_of_billing_month(validated_month)

    stmt = (
        select(Student)
        .options(selectinload(Student.enrollments).joinedload(Enrollment.teacher))
        .where(Student.is_active.is_(True))
    )
    if grade and grade.strip():
        stmt = stmt.where(Student.grade.ilike(f"%{grade.strip()}%"))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            Student.full_name.ilike(pattern)
            | Student.phone.ilike(pattern)
            | Student.guardian_phone.ilike(pattern)
        )

    students = list(db.scalars(stmt.order_by(Student.full_name.asc())).all())
    if not students:
        return []

    student_ids = [s.id for s in students]
    payments = list(
        db.scalars(
            select(Payment).where(
                Payment.student_id.in_(student_ids),
                Payment.billing_month == validated_month,
            )
        ).all()
    )

    payments_by_student: dict[int, dict[int, Payment]] = {}
    for p in payments:
        payments_by_student.setdefault(p.student_id, {})[p.enrollment_id] = p

    results: List[StudentMonthlyDuesSummary] = []
    for student in students:
        summary = _build_student_dues_summary(
            student=student,
            billing_month=validated_month,
            cutoff_date=cutoff_date,
            payments_by_enrollment=payments_by_student.get(student.id, {}),
            teacher_id_filter=teacher_id,
        )
        if summary.payment_status == "NO_ACTIVE_ENROLLMENTS":
            continue
        if status_filter and summary.payment_status != status_filter.upper():
            continue
        results.append(summary)

    return results