from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.core.security import hash_password
from app.models import Base, Admin
from app.api.v1.router import api_v1_router
from app.web.routes import web_router

BASE_DIR = Path(__file__).resolve().parent


def seed_default_admin():
    """Ensure at least one admin account exists on first startup."""
    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(Admin).where(Admin.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        if not existing_admin:
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

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(api_v1_router)
app.include_router(web_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}