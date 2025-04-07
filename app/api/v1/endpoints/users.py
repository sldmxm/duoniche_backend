import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_user_service
from app.api.errors import NotFoundError
from app.api.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.entities.user import User
from app.core.services.user import UserService

logger = logging.getLogger(__name__)
router = APIRouter()

# TODO: Новых пользователей лучше отслеживать здесь или в Core, не в боте
# USER_METRICS = {
#     "registration_count": Counter(
#         "user_registration_count", "Total number of user registrations"
#     ),
# }


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
    return await user_service.get_or_create(user)


@router.get(
    '/{telegram_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_telegram_id(
    telegram_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get user by telegram_id.
    """
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        raise NotFoundError(detail='User not found')
    return user


@router.put(
    '/{user_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user_by_user_id(
    user_id: int,
    user_data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Update user by user_id.
    """
    user = User(**user_data.model_dump())
    user.user_id = user_id
    try:
        updated_user = await user_service.update(user)
    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e
    return updated_user
