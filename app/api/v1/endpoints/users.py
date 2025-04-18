import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_user_progress_service, get_user_service
from app.api.errors import NotFoundError
from app.api.schemas.exercise import ExerciseSchema
from app.api.schemas.next_action_result import NextActionSchema
from app.api.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.services.user import UserService
from app.core.services.user_progress import UserProgressService

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
    logger.debug(f'User data: {user}')
    user_from_service = await user_service.get_or_create(user)
    logger.debug(f'Saved user: {user_from_service}')
    return user_from_service


@router.get(
    '/by-telegram-id/{telegram_id}',
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
        updated_user = await user_service.update(
            user_id=user_id,
            username=user.username,
            name=user.name,
            user_language=user.user_language,
        )
    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e
    return updated_user


@router.get(
    '/{user_id}/next_action/',
    response_model=NextActionSchema,
    response_model_exclude_none=True,
    summary='Get next action for user',
    description='Get a next action for the user',
)
async def get_next_action(
    user_progress_service: Annotated[
        UserProgressService, Depends(get_user_progress_service)
    ],
    user_id: int,
) -> NextActionSchema:
    """
    Get a next action for the user
    """
    try:
        next_action: NextAction = await user_progress_service.get_next_action(
            user_id=user_id,
        )
        output = NextActionSchema(
            exercise=(
                ExerciseSchema.model_validate(
                    next_action.exercise.model_dump()
                )
                if next_action.exercise
                else None
            ),
            action=next_action.action,
            message=next_action.message,
            pause=next_action.pause,
        )
        return output

    except ValueError as e:
        logger.error(f'Invalid parameter value: {str(e)}')

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e
