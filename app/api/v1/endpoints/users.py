import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_user_service
from app.api.errors import NotFoundError
from app.api.schemas.user import UserCreate, UserResponse
from app.core.entities.user import User
from app.core.services.user import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.put(
    '/',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_or_create_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get or create a user.
    """
    user = User(**user_data.model_dump())
    return await user_service.get_or_create_user(user)


@router.get(
    '/{telegram_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_telegram_id(
    telegram_id: int,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get user by telegram_id.
    """
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise NotFoundError(detail='User not found')
    return user
