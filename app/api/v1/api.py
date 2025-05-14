from fastapi import APIRouter

from app.api.v1.endpoints import exercises, next_action, notifications, users

api_router = APIRouter()
api_router.include_router(
    exercises.router,
    prefix='/exercises',
    tags=['exercises'],
)
api_router.include_router(
    users.router,
    prefix='/users',
    tags=['users'],
)
api_router.include_router(
    next_action.router,
    prefix='/users',
    tags=['users'],
)

api_router.include_router(
    notifications.router,
    prefix='/notifications',
    tags=['notifications'],
)
