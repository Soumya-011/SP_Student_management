from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

BILLING_MONTH_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validate_YYYY_MM(value: str) -> str:
    cleaned = value.strip()
    if not BILLING_MONTH_REGEX.match(cleaned):
        raise ValueError("billing_month must be in 'YYYY-MM' format (e.g., '2026-10')")
    return cleaned


class PaymentItemCreate(BaseModel):
    enrollment_id: int
    amount_paid: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Leave null to auto-charge the enrollment's agreed monthly_fee",
    )


class BatchPaymentCreate(BaseModel):
    student_id: int
    billing_month: str = Field(..., examples=["2026-10"])
    payment_date: Optional[date] = None
    payment_method: str = Field(default="Cash", min_length=2, max_length=30)
    notes: Optional[str] = Field(default=None, max_length=255)
    items: List[PaymentItemCreate] = Field(
        ..., min_length=1, description="List of teacher enrollments being paid for"
    )

    @field_validator("billing_month")
    @classmethod
    def check_billing_month(cls, v: str) -> str:
        return validate_YYYY_MM(v)

    @model_validator(mode="after")
    def check_unique_enrollment_ids(self):
        seen = set()
        for item in self.items:
            if item.enrollment_id in seen:
                raise ValueError(
                    f"Duplicate enrollment_id {item.enrollment_id} in payment request"
                )
            seen.add(item.enrollment_id)
        return self


class PaymentResponse(BaseModel):
    id: int
    receipt_no: str
    student_id: int
    student_name: str = ""
    enrollment_id: int
    teacher_id: int = 0
    teacher_name: str = ""
    subject: str = ""
    billing_month: str
    amount_paid: Decimal
    payment_date: date
    payment_method: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def flatten_relationships(cls, data: Any) -> Any:
        if hasattr(data, "enrollment") and data.enrollment is not None:
            enrollment = data.enrollment
            teacher = getattr(enrollment, "teacher", None)
            student = getattr(data, "student", None)
            return {
                "id": data.id,
                "receipt_no": data.receipt_no,
                "student_id": data.student_id,
                "student_name": student.full_name if student else "",
                "enrollment_id": data.enrollment_id,
                "teacher_id": enrollment.teacher_id,
                "teacher_name": teacher.full_name if teacher else "",
                "subject": enrollment.subject,
                "billing_month": data.billing_month,
                "amount_paid": data.amount_paid,
                "payment_date": data.payment_date,
                "payment_method": data.payment_method,
                "notes": data.notes,
                "created_at": data.created_at,
            }
        return data


class BatchPaymentResponse(BaseModel):
    receipt_no: str
    student_id: int
    student_name: str
    billing_month: str
    payment_date: date
    payment_method: str
    total_amount_paid: Decimal
    payments: List[PaymentResponse]


class EnrollmentFeeStatus(BaseModel):
    """Represents the payment status of a single teacher/subject for a student in a billing month."""
    enrollment_id: int
    teacher_id: int
    teacher_name: str
    subject: str
    monthly_fee: Decimal
    is_paid: bool
    amount_paid: Decimal = Decimal("0.00")
    payment_id: Optional[int] = None
    receipt_no: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None


class StudentMonthlyDuesSummary(BaseModel):
    """Complete monthly fee ledger for a student (used in both checkout and center-wide dues report)."""
    student_id: int
    student_name: str
    phone: Optional[str] = None
    guardian_name: str
    guardian_phone: str
    grade: str
    billing_month: str
    total_expected_fee: Decimal
    total_paid: Decimal
    total_pending: Decimal
    payment_status: Literal["PAID", "PARTIAL", "UNPAID", "NO_ACTIVE_ENROLLMENTS"]
    enrollments: List[EnrollmentFeeStatus]