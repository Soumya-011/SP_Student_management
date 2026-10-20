from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditLog(Base):
    """
    Immutable system-wide audit trail for all database mutations and auth events.
    Inspect directly via PostgreSQL: SELECT * FROM audit_logs ORDER BY created_at DESC;
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    admin_username: Mapped[str] = mapped_column(String(50), index=True, nullable=False, default="system")
    action: Mapped[str] = mapped_column(
        String(40), index=True, nullable=False
    )  # CREATE, UPDATE, DELETE, LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, PASSWORD_CHANGE
    entity_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # students, teachers, enrollments, schedules, payments, admins, auth
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    changes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )