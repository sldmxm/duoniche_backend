import json
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

from app.api.cache import validation_cache
from app.api.dependencies import get_exercise_service, get_user_service
from app.api.errors import NotFoundError
from app.api.schemas.answer import FillInTheBlankAnswerSchema
from app.api.schemas.exercise import ExerciseSchema
from app.api.schemas.validation_result import ValidationResultSchema
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.value_objects.answer import FillInTheBlankAnswer

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
    user_service: Annotated[UserService, Depends(get_user_service)],
    language_level: Annotated[str, Body(description='Language level')],
    exercise_type: Annotated[
        ExerciseType, Body(description='Type of exercise')
    ],
    user_id: Annotated[int, Body(description='User ID')],
    topic: Annotated[str, Body(description='Exercise topic')] = 'general',
) -> ExerciseSchema:
    """
    Get or create a new exercise for the user based on their
    language level and preferred exercise type.

    Returns a 404 error if no suitable exercise is found.
    """
    try:
        user = await user_service.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                'User with provided ID not found in the database'
            )

        exercise: Optional[
            Exercise
        ] = await exercise_service.get_or_create_new_exercise(
            user=user,
            language_level=language_level,
            exercise_type=exercise_type.value,
            topic=topic,
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
    user_service: Annotated[UserService, Depends(get_user_service)],
    exercise_id: Annotated[int, Body(description='Exercise ID')],
    answer: Annotated[
        FillInTheBlankAnswerSchema, Body(description="User's answer")
    ],
    user_id: Annotated[int, Body(description='User ID')],
) -> ValidationResultSchema:
    """
    Validate a user's answer to an exercise and provide feedback.

    Returns a 404 error if the exercise is not found.
    """
    try:
        user = await user_service.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                'User with provided ID not found in the database'
            )

        exercise: Optional[
            Exercise
        ] = await exercise_service.get_exercise_by_id(exercise_id)
        if not exercise:
            raise NotFoundError(f'Exercise with ID {exercise_id} not found')

        exercise_attempt = await exercise_service.new_exercise_attempt(
            user=user,
            exercise=exercise,
            answer=FillInTheBlankAnswer(**answer.model_dump()),
            is_correct=None,
            feedback=None,
            exercise_answer_id=None,
        )

        cache_key = (
            f'validation_{exercise_id}_{hash(json.dumps(answer.model_dump()))}'
        )

        validation_result = await validation_cache.get_or_create_validation(
            key=cache_key,
            validation_func=lambda: exercise_service.validate_exercise_answer(
                user,
                exercise,
                FillInTheBlankAnswer(**answer.model_dump()),
            ),
        )

        if exercise_attempt.attempt_id is None:
            raise ValueError('Exercise attempt attempt_id must not be None')

        exercise_attempt = await exercise_service.update_exercise_attempt(
            attempt_id=exercise_attempt.attempt_id,
            is_correct=validation_result.is_correct,
            feedback=validation_result.feedback,
            exercise_answer_id=validation_result.answer_id,
        )

        if exercise_attempt.is_correct is None:
            raise ValueError('Exercise attempt is_correct must not be None')

        return ValidationResultSchema(
            is_correct=exercise_attempt.is_correct,
            feedback=exercise_attempt.feedback,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e
