import logging
from typing import Annotated, Optional, Union

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    status,
)
from fastapi.routing import APIRoute

from app.api.dependencies import (
    get_exercise_service,
    get_user_bot_profile_service,
    get_user_service,
)
from app.api.errors import NotFoundError
from app.api.schemas.answer import (
    ChooseAnswerSchema,
    FillInTheBlankAnswerSchema,
)
from app.api.schemas.validation_result import ValidationResultSchema
from app.core.entities.exercise import Exercise
from app.core.entities.user_bot_profile import BotID
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.value_objects.answer import (
    create_answer_model_validate,
)

logger = logging.getLogger(__name__)
router = APIRouter(route_class=APIRoute)


async def _validate_exercise_attempt_handler(
    exercise_service: ExerciseService,
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    answer: Union[
        FillInTheBlankAnswerSchema,
        ChooseAnswerSchema,
    ],
    user_id: int,
    body_exercise_id: Optional[int] = None,
    path_exercise_id: Optional[int] = None,
) -> ValidationResultSchema:
    effective_exercise_id: Optional[int] = None

    if path_exercise_id is not None:
        effective_exercise_id = path_exercise_id
        if (
            body_exercise_id is not None
            and body_exercise_id != path_exercise_id
        ):
            logger.warning(
                f'Exercise ID provided in both path ({path_exercise_id}) '
                f'and body ({body_exercise_id}). Path parameter is used.'
            )
    elif body_exercise_id is not None:
        effective_exercise_id = body_exercise_id

    if effective_exercise_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                'Exercise ID must be provided either in '
                'the path (e.g., /exercises/123/validate/) '
                'or in the request body (for legacy /validate/ calls).'
            ),
        )

    try:
        user = await user_service.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                'User with provided ID not found in the database'
            )

        exercise: Optional[
            Exercise
        ] = await exercise_service.get_exercise_by_id(effective_exercise_id)
        if not exercise:
            raise NotFoundError(
                f'Exercise with ID {effective_exercise_id} not found'
            )

        if exercise.exercise_type.value != answer.exercise_type:
            # Используем f-string для более чистого вывода
            raise ValueError(
                f'Answer type "{answer.exercise_type}" does not for exercise: '
                f'"{exercise.exercise_type.value}".'
            )

        try:
            bot_id = BotID(exercise.exercise_language)
        except ValueError as e:
            logger.error(
                f"Invalid exercise_language '{exercise.exercise_language}' "
                f'for exercise ID {effective_exercise_id} '
                f'cannot be mapped to BotID.'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Internal server error: '
                'Invalid exercise language configuration.',
            ) from e

        user_bot_profile = await user_bot_profile_service.get(
            user_id=user_id,
            bot_id=bot_id,
        )
        if not user_bot_profile:
            raise NotFoundError(
                'User bot profile with provided ID not found in the database'
            )

        user_answer = create_answer_model_validate(answer.model_dump())

        exercise_attempt = await exercise_service.validate_exercise_attempt(
            user_id=user_id,
            user_language=user_bot_profile.user_language,
            last_exercise_at=user_bot_profile.last_exercise_at,
            exercise=exercise,
            answer=user_answer,
        )

        if exercise_attempt.is_correct is None:
            logger.error(
                f'exercise_attempt.is_correct is None '
                f'for exercise {effective_exercise_id}, user {user_id}'
            )
            raise ValueError(
                'Validation result is_correct must not be None after attempt.'
            )

        logger.debug(f'{exercise_attempt=}')

        return ValidationResultSchema(
            is_correct=exercise_attempt.is_correct,
            feedback=exercise_attempt.feedback,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'Invalid input: {str(e)}',
        ) from e


@router.post(
    '/{path_exercise_id}/validate/',
    response_model=ValidationResultSchema,
    response_model_exclude_none=True,
    summary="Validate a user's exercise attempt (ID in path)",
    description=(
        "Validates the user's answer to an exercise "
        '(ID from path) and returns feedback.'
    ),
)
async def validate_exercise_attempt(
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    answer: Annotated[
        Union[
            FillInTheBlankAnswerSchema,
            ChooseAnswerSchema,
        ],
        Body(description="User's answer"),
    ],
    user_id: Annotated[int, Body(description='User ID', ge=1)],
    path_exercise_id: Annotated[
        int,
        Path(description='Exercise ID from path', ge=1),
    ],
) -> ValidationResultSchema:
    """
    Validate a user's answer to an exercise and provide feedback.

    Returns a 404 error if the exercise is not found.
    """
    return await _validate_exercise_attempt_handler(
        exercise_service=exercise_service,
        user_service=user_service,
        user_bot_profile_service=user_bot_profile_service,
        answer=answer,
        user_id=user_id,
        body_exercise_id=None,
        path_exercise_id=path_exercise_id,
    )


@router.post(
    '/validate/',
    response_model=ValidationResultSchema,
    response_model_exclude_none=True,
    summary="Validate a user's exercise attempt (ID in body - Legacy)",
    description=(
        "Validates the user's answer to an exercise "
        '(ID from body) and returns feedback.'
    ),
    deprecated=True,
)
async def validate_exercise_attempt_legacy(
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    answer: Annotated[
        Union[
            FillInTheBlankAnswerSchema,
            ChooseAnswerSchema,
        ],
        Body(description="User's answer"),
    ],
    user_id: Annotated[int, Body(description='User ID', ge=1)],
    body_exercise_id: Annotated[
        int,
        Body(
            alias='exercise_id',
            description='Exercise ID from body (legacy)',
            ge=1,
        ),
    ],
) -> ValidationResultSchema:
    """
    Validate a user's answer to an exercise and provide feedback.
    (Legacy path - ID from body)
    Returns a 404 error if the exercise is not found.
    """
    return await _validate_exercise_attempt_handler(
        exercise_service=exercise_service,
        user_service=user_service,
        user_bot_profile_service=user_bot_profile_service,
        answer=answer,
        user_id=user_id,
        body_exercise_id=body_exercise_id,
        path_exercise_id=None,
    )
