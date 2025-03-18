import logging
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    status,
)
from fastapi.routing import APIRoute

from app.api.dependencies import get_exercise_service
from app.api.errors import NotFoundError
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.schemas.answer import FillInTheBlankAnswerSchema
from app.schemas.exercise import ExerciseSchema
from app.schemas.validation_result import ValidationResultSchema

logger = logging.getLogger(__name__)
router = APIRouter(route_class=APIRoute)


@router.post(
    '/new',
    response_model=ExerciseSchema,
    response_model_exclude_none=True,
    summary='Get a new exercise',
    description=(
        'Returns a new exercise '
        "based on user's language level and exercise type"
    ),
)
async def get_or_create_new_exercise(
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    language_level: Annotated[str, Body(description='Language level')],
    exercise_type: Annotated[
        ExerciseType, Body(description='Type of exercise')
    ],
    user_id: Annotated[str, Body()],
    telegram_id: Annotated[str, Body()],
    user_language: Annotated[str, Body()],
    target_language: Annotated[str, Body()],
    username: Annotated[Optional[str], Body()] = '',
    name: Annotated[Optional[str], Body()] = '',
) -> ExerciseSchema:
    """
    Get or create a new exercise for the user based on their
    language level and preferred exercise type.

    Returns a 404 error if no suitable exercise is found.
    """
    try:
        # TODO: брать из БД данные юзера, принимать только id,
        #   сейчас криво - создается пользователь с target_language
        user = User(
            user_id=int(user_id),
            telegram_id=int(telegram_id),
            username=username,
            name=name,
            user_language=user_language,
            target_language=target_language,
        )

        exercise: Optional[
            Exercise
        ] = await exercise_service.get_or_create_new_exercise(
            user, language_level, exercise_type.value
        )

        logger.debug(f'Exercise: {exercise}')

        if not exercise:
            raise NotFoundError(
                'No suitable exercise found for the provided criteria'
            )

        return ExerciseSchema.model_validate(exercise.model_dump())

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e


@router.post(
    '/validate',
    response_model=ValidationResultSchema,
    response_model_exclude_none=True,
    summary="Validate a user's exercise attempt",
    description=(
        "Validates the user's answer to an exercise and returns feedback"
    ),
)
async def validate_exercise_attempt(
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    exercise_id: Annotated[int, Body(description='Exercise ID')],
    answer: Annotated[
        FillInTheBlankAnswerSchema, Body(description="User's answer")
    ],
    user_id: Annotated[str, Body()],
    telegram_id: Annotated[str, Body()],
    user_language: Annotated[str, Body()],
    target_language: Annotated[str, Body()],
    username: Annotated[Optional[str], Body()] = None,
    name: Annotated[Optional[str], Body()] = None,
) -> ValidationResultSchema:
    """
    Validate a user's answer to an exercise and provide feedback.

    Returns a 404 error if the exercise is not found.
    """
    try:
        user = User(
            user_id=int(user_id),
            telegram_id=int(telegram_id),
            username=username,
            name=name,
            user_language=user_language,
            target_language=target_language,
        )

        exercise: Optional[
            Exercise
        ] = await exercise_service.get_exercise_by_id(exercise_id)
        if not exercise:
            raise NotFoundError(f'Exercise with ID {exercise_id} not found')

        exercise_attempt: ExerciseAttempt = (
            await exercise_service.validate_exercise_attempt(
                user,
                exercise,
                FillInTheBlankAnswer(**answer.model_dump()),
            )
        )
        return ValidationResultSchema(
            is_correct=exercise_attempt.is_correct,
            feedback=exercise_attempt.feedback,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e
