import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_user_service
from app.api.schemas.user import UserCreate, UserResponse
from app.core.entities.user import User
from app.core.services.user import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    '/register',
    response_model=UserResponse,
    # TODO: Возвращать 200, если уже был зарегистрирован
    status_code=status.HTTP_201_CREATED,
)
async def get_or_create_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Register a new user or return an existing user.
    """
    user_to_check = User(**user_data.model_dump())
    user = await user_service.get_or_create_user(user_to_check)
    return user


@router.get(
    '/{telegram_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_telegram_id(
    telegram_id: int,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> Optional[User]:
    """
    Get user by telegram_id.
    """
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )
    return user
