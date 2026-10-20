from contextvars import ContextVar
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

# Request-scoped context variables populated automatically by FastAPI middleware/deps
audit_admin_id: ContextVar[Optional[int]] = ContextVar("audit_admin_id", default=None)
audit_admin_username: ContextVar[Optional[str]] = ContextVar("audit_admin_username", default=None)
audit_ip_address: ContextVar[Optional[str]] = ContextVar("audit_ip_address", default=None)
audit_user_agent: ContextVar[Optional[str]] = ContextVar("audit_user_agent", default=None)

SENSITIVE_COLUMNS = {"password_hash"}
AUDITED_TABLES = {
    "admins",
    "teachers",
    "students",
    "enrollments",
    "schedules",
    "payments",
}


def set_audit_actor(admin_id: Optional[int], username: Optional[str]) -> None:
    audit_admin_id.set(admin_id)
    audit_admin_username.set(username)


def set_audit_request_meta(ip_address: Optional[str], user_agent: Optional[str]) -> None:
    audit_ip_address.set(ip_address)
    audit_user_agent.set(user_agent)


def _json_safe(val: Any) -> Any:
    """Convert Decimal, date, time, datetime, and lists into JSON-serializable primitives."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (datetime, date, time)):
        return val.isoformat()
    if isinstance(val, list):
        return [_json_safe(item) for item in val]
    return val


def _extract_model_snapshot(instance: Any) -> Dict[str, Any]:
    mapper = inspect(instance).mapper
    snapshot: Dict[str, Any] = {}
    for attr in mapper.column_attrs:
        col_name = attr.key
        raw_val = getattr(instance, col_name, None)
        if col_name in SENSITIVE_COLUMNS:
            snapshot[col_name] = "[REDACTED]"
        else:
            snapshot[col_name] = _json_safe(raw_val)
    return snapshot


def _extract_update_diff(instance: Any) -> Dict[str, Dict[str, Any]]:
    state = inspect(instance)
    diff: Dict[str, Dict[str, Any]] = {}
    for attr in state.mapper.column_attrs:
        col_name = attr.key
        hist = state.attrs[col_name].history
        if not hist.has_changes():
            continue

        old_val = hist.deleted[0] if hist.deleted else None
        new_val = hist.added[0] if hist.added else getattr(instance, col_name, None)

        if old_val == new_val:
            continue

        if col_name in SENSITIVE_COLUMNS:
            diff[col_name] = {"old": "[REDACTED]", "new": "[REDACTED_CHANGED]"}
        else:
            diff[col_name] = {
                "old": _json_safe(old_val),
                "new": _json_safe(new_val),
            }
    return diff


def log_auth_event(
    db: Session,
    action: str,
    admin_id: Optional[int] = None,
    username: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Explicitly log authentication & security events (LOGIN, LOGOUT, PASSWORD_CHANGE)."""
    from app.models.audit_log import AuditLog

    entry = AuditLog(
        admin_id=admin_id if admin_id is not None else audit_admin_id.get(),
        admin_username=username if username is not None else (audit_admin_username.get() or "system"),
        action=action,
        entity_type="auth",
        entity_id=str(admin_id) if admin_id else None,
        changes=details or {},
        ip_address=audit_ip_address.get(),
        user_agent=audit_user_agent.get(),
    )
    db.add(entry)
    db.commit()


def register_audit_listeners() -> None:
    """
    Hooks into SQLAlchemy Session flush events to automatically capture
    CREATE, UPDATE, and DELETE operations across all domain tables.
    """
    from app.models.audit_log import AuditLog

    @event.listens_for(Session, "before_flush")
    def capture_dirty_and_deleted(session: Session, flush_context, instances) -> None:
        if not hasattr(session, "_pending_audit_logs"):
            session._pending_audit_logs = []
        if not hasattr(session, "_pending_new_objects"):
            session._pending_new_objects = []

        # Track new objects so we can read their generated primary key in after_flush
        for obj in session.new:
            table_name = getattr(obj, "__tablename__", None)
            if table_name in AUDITED_TABLES:
                session._pending_new_objects.append(obj)

        # Capture UPDATE diffs before flush clears attribute history
        for obj in session.dirty:
            if session.is_modified(obj, include_collections=False):
                table_name = getattr(obj, "__tablename__", None)
                if table_name in AUDITED_TABLES:
                    diff = _extract_update_diff(obj)
                    if diff:
                        pk = getattr(obj, "id", None)
                        session._pending_audit_logs.append(
                            AuditLog(
                                admin_id=audit_admin_id.get(),
                                admin_username=audit_admin_username.get() or "system",
                                action="UPDATE",
                                entity_type=table_name,
                                entity_id=str(pk) if pk is not None else None,
                                changes=diff,
                                ip_address=audit_ip_address.get(),
                                user_agent=audit_user_agent.get(),
                            )
                        )

        # Capture DELETE snapshots before rows are removed
        for obj in session.deleted:
            table_name = getattr(obj, "__tablename__", None)
            if table_name in AUDITED_TABLES:
                pk = getattr(obj, "id", None)
                session._pending_audit_logs.append(
                    AuditLog(
                        admin_id=audit_admin_id.get(),
                        admin_username=audit_admin_username.get() or "system",
                        action="DELETE",
                        entity_type=table_name,
                        entity_id=str(pk) if pk is not None else None,
                        changes={"deleted_record": _extract_model_snapshot(obj)},
                        ip_address=audit_ip_address.get(),
                        user_agent=audit_user_agent.get(),
                    )
                )

    @event.listens_for(Session, "after_flush")
    def persist_audit_entries(session: Session, flush_context) -> None:
        # Guard against recursive loop when flushing AuditLog objects themselves
        if getattr(session, "_flushing_audit", False):
            return

        new_objs = getattr(session, "_pending_new_objects", [])
        pending_logs = getattr(session, "_pending_audit_logs", [])

        for obj in new_objs:
            table_name = getattr(obj, "__tablename__", None)
            pk = getattr(obj, "id", None)
            pending_logs.append(
                AuditLog(
                    admin_id=audit_admin_id.get(),
                    admin_username=audit_admin_username.get() or "system",
                    action="CREATE",
                    entity_type=table_name,
                    entity_id=str(pk) if pk is not None else None,
                    changes={"created_record": _extract_model_snapshot(obj)},
                    ip_address=audit_ip_address.get(),
                    user_agent=audit_user_agent.get(),
                )
            )

        session._pending_new_objects = []
        session._pending_audit_logs = []

        if pending_logs:
            session._flushing_audit = True
            try:
                for log_entry in pending_logs:
                    session.add(log_entry)
            finally:
                session._flushing_audit = False