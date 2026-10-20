from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, hash_password, create_access_token
from app.core.audit import log_auth_event, set_audit_actor
from app.models.admin import Admin
from app.schemas.auth import Token, AdminResponse, PasswordChangeRequest
from app.api.deps import get_current_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    admin = db.scalar(select(Admin).where(Admin.username == form_data.username))
    if not admin or not verify_password(form_data.password, admin.password_hash):
        log_auth_event(
            db,
            action="LOGIN_FAILED",
            username=form_data.username,
            details={"reason": "Invalid username or password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    set_audit_actor(admin.id, admin.username)
    access_token = create_access_token(subject=admin.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )

    log_auth_event(
        db,
        action="LOGIN_SUCCESS",
        admin_id=admin.id,
        username=admin.username,
        details={"method": "password"},
    )
    return Token(access_token=access_token)


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    log_auth_event(
        db,
        action="LOGOUT",
        admin_id=current_admin.id,
        username=current_admin.username,
    )
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out"}


@router.post("/change-password")
def change_admin_password(
    payload: PasswordChangeRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Verifies the current password, updates the bcrypt hash, rotates the JWT cookie,
    and records the event in audit_logs.
    """
    if not verify_password(payload.current_password, current_admin.password_hash):
        log_auth_event(
            db,
            action="PASSWORD_CHANGE_FAILED",
            admin_id=current_admin.id,
            username=current_admin.username,
            details={"reason": "Incorrect current password"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_admin.password_hash = hash_password(payload.new_password)
    db.commit()

    # Rotate JWT cookie so current browser session stays seamlessly authenticated
    new_token = create_access_token(subject=current_admin.username)
    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )

    log_auth_event(
        db,
        action="PASSWORD_CHANGE",
        admin_id=current_admin.id,
        username=current_admin.username,
        details={"status": "Password hash rotated"},
    )
    return {"message": "Password updated successfully"}


@router.get("/me", response_model=AdminResponse)
def read_current_admin(current_admin: Admin = Depends(get_current_admin)):
    return current_admin