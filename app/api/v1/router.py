from fastapi import APIRouter
from app.api.v1 import auth, teachers, schedules, students, payments

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(teachers.router)
api_v1_router.include_router(schedules.router)
api_v1_router.include_router(students.router)
api_v1_router.include_router(payments.router)