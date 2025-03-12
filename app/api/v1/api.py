from fastapi import APIRouter

from app.api.v1.endpoints import exercises

api_router = APIRouter()
api_router.include_router(
    exercises.router, prefix='/exercises', tags=['exercises']
)
