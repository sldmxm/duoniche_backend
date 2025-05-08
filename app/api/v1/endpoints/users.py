import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_user_bot_profile_service,
    get_user_progress_service,
    get_user_service,
)
from app.api.errors import NotFoundError
from app.api.schemas.exercise import ExerciseSchema
from app.api.schemas.next_action_result import NextActionSchema
from app.api.schemas.user import UserCreate, UserResponse, UserUpdate
from app.api.schemas.user_status import (
    ReportBlockResponse,
    UserBlockReportPayload,
)
from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.metrics import BACKEND_USER_METRICS

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
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
) -> UserResponse:
    """
    Get or create a user.
    """
    # TODO: Переписать на users/bots/{bot_id}
    try:
        user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            name=user_data.name,
            telegram_data=user_data.telegram_data,
        )
        user_from_service, is_created = await user_service.get_or_create(user)
        if not user_from_service or not user_from_service.user_id:
            raise ValueError('User not found')

        bot_id = BotID(user_data.target_language)
        user_bot_profile, _ = await user_bot_profile_service.get_or_create(
            user_id=user_from_service.user_id,
            bot_id=bot_id,
            user_language=user_data.user_language,
            language_level=DEFAULT_LANGUAGE_LEVEL,
        )

        if is_created:
            BACKEND_USER_METRICS['new'].labels(
                cohort=user_from_service.cohort,
                plan=user_from_service.plan,
                target_language=user_data.target_language,
                user_language=user_bot_profile.user_language,
                language_level=user_bot_profile.language_level.value,
            ).inc()

        output = _create_user_for_response(
            user=user_from_service,
            user_bot_profile=user_bot_profile,
        )

    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e

    return output


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
    # TODO: Учесть блокировку бота пользователем,
    #  брать на входе bot_id
    #  чтобы заставлять регистрироваться заново
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user:
        raise NotFoundError(detail='User not found')
    return user


@router.put(
    '/{user_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user_by_user_id_legacy(
    user_id: int,
    user_data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
) -> UserResponse:
    """
    Legacy endpoint. Update user by user_id.
    """
    # TODO:
    #  Убрать лишние поля из output
    #  Переписать на две ручки:
    #  - для изменения настроек пользователя
    #  - для изменений настроек бота

    try:
        updated_user = await user_service.update(
            user_id=user_id,
            username=user_data.username,
            name=user_data.name,
            telegram_data=user_data.telegram_data,
        )

        bot = BotID(user_data.target_language)
        updated_user_bot_profile = (
            await user_bot_profile_service.update_profile(
                user_id=user_id,
                bot_id=bot,
                user_language=user_data.user_language,
            )
        )
        output = _create_user_for_response(
            user=updated_user,
            user_bot_profile=updated_user_bot_profile,
        )
    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e
    return output


@router.get(
    '/{user_id}/next_action/',
    response_model=NextActionSchema,
    response_model_exclude_none=True,
    summary='Get next action for user',
    description='Get a next action for the user',
)
async def get_next_action_legacy(
    user_progress_service: Annotated[
        UserProgressService, Depends(get_user_progress_service)
    ],
    user_id: int,
) -> NextActionSchema:
    """
    Legacy endpoint. Get a next action for the user
    """
    # TODO: Удалить после перехода бота и *миниаппа* на новый url
    logger.warning('Legacy endpoint. Get a next action for the user')
    try:
        bot_id = BotID.BG
        next_action: NextAction = await user_progress_service.get_next_action(
            user_id=user_id, bot_id=bot_id
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


@router.get(
    '{user_id}/bots/{bot_id}/next-action/',
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
    bot_id: str,
) -> NextActionSchema:
    """
    Get a next action for the user
    """
    try:
        bot = BotID(bot_id)
        next_action: NextAction = await user_progress_service.get_next_action(
            user_id=user_id, bot_id=bot
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


@router.post(
    '/{user_id}/bots/{bot_id}/block/',
    response_model=ReportBlockResponse,
    summary='Set bot as blocked by user',
    description='Set bot as blocked by user',
)
async def block_bot(
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_id: int,
    bot_id: str,
    report: UserBlockReportPayload,
):
    user = await user_service.get_by_id(user_id)
    if not user or user.telegram_id != report.telegram_id:
        raise NotFoundError(detail='User not found')
    try:
        bot = BotID(bot_id)
        await user_bot_profile_service.mark_user_blocked(
            user_id=user_id, bot_id=bot, reason=report.reason
        )
    except ValueError as e:
        logger.error(f'Invalid parameter value: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e

    return ReportBlockResponse(status='ok')


def _create_user_for_response(
    user: User, user_bot_profile: UserBotProfile
) -> UserResponse:
    if not user or not user_bot_profile or not user.user_id:
        raise ValueError('User not found')
    return UserResponse(
        user_id=user.user_id,
        telegram_id=user.telegram_id,
        username=user.username,
        name=user.name,
        telegram_data=user.telegram_data,
        cohort=user.cohort,
        plan=user.plan,
        user_language=user_bot_profile.user_language,
        target_language=user_bot_profile.bot_id.value,
        language_level=user_bot_profile.language_level.value,
    )
