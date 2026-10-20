from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.core.security import hash_password
from app.core.audit import (
    register_audit_listeners,
    set_audit_actor,
    set_audit_request_meta,
)
from app.models import Base, Admin
from app.api.v1.router import api_v1_router
from app.web.routes import web_router

BASE_DIR = Path(__file__).resolve().parent

# Register SQLAlchemy Session before_flush / after_flush audit hooks
register_audit_listeners()


def seed_default_admin():
    """Ensure at least one admin account exists on first startup."""
    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(Admin).where(Admin.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        if not existing_admin:
            set_audit_actor(None, "system_seed")
            admin = Admin(
                username=settings.DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            )
            db.add(admin)
            db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_admin()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def audit_context_middleware(request: Request, call_next):
    """Populate request IP address and User-Agent into ContextVars for every request."""
    set_audit_actor(None, None)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:255]
    set_audit_request_meta(client_ip, user_agent)
    return await call_next(request)


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(api_v1_router)
app.include_router(web_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}