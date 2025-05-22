import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_user_progress_service,
)
from app.api.schemas.exercise import ExerciseSchema
from app.api.schemas.next_action_result import NextActionSchema
from app.core.entities.next_action_result import NextAction
from app.core.entities.user_bot_profile import BotID
from app.core.services.user_progress import UserProgressService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_next_action(
    user_progress_service: UserProgressService,
    user_id: int,
    path_bot_id: Optional[str] = None,
) -> NextActionSchema:
    try:
        if path_bot_id is not None:
            try:
                bot_id = BotID(path_bot_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Invalid bot_id in path: '{path_bot_id}'. "
                        f'Valid values are: '
                        f'{[member.value for member in BotID]}'
                    ),
                ) from e
        else:
            logger.warning(
                f'Legacy endpoint /{user_id}/next_action/ called. '
                f'Defaulting to bot_id={BotID.BG.value}'
            )
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
            payment_info=next_action.payment_info,
        )
        return output

    except ValueError as e:
        logger.error(f'Invalid parameter value: {str(e)}')

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e


@router.get(
    '/{user_id}/next_action/',
    response_model=NextActionSchema,
    response_model_exclude_none=True,
    summary='Get next action for user (legacy: bot_id = BotID.BG)',
    description='Get a next action for the user',
    deprecated=True,
)
async def get_next_action_legacy(
    user_progress_service: Annotated[
        UserProgressService, Depends(get_user_progress_service)
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
) -> NextActionSchema:
    """
    Legacy endpoint. Get a next action for the user
    """
    # TODO: Удалить после перехода миниаппа на новый url
    return await _get_next_action(
        user_progress_service=user_progress_service,
        user_id=user_id,
        path_bot_id=None,
    )


@router.get(
    '/{user_id}/bots/{bot_id}/next-action/',
    response_model=NextActionSchema,
    response_model_exclude_none=True,
    summary='Get next action for user',
    description='Get a next action for the user',
)
async def get_next_action(
    user_progress_service: Annotated[
        UserProgressService, Depends(get_user_progress_service)
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    bot_id: Annotated[
        str, Path(description='Bot ID from path (e.g., Bulgarian, English)')
    ],
) -> NextActionSchema:
    """
    Get a next action for the user
    """
    return await _get_next_action(
        user_progress_service=user_progress_service,
        user_id=user_id,
        path_bot_id=bot_id,
    )
