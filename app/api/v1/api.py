from fastapi import APIRouter

from app.api.v1.endpoints import exercises, users

api_router = APIRouter()
api_router.include_router(
    exercises.router,
    prefix='/exercises',
    tags=['exercises'],
)
api_router.include_router(users.router, prefix='/api/v1/users', tags=['users'])
