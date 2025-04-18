import logging
from typing import Annotated, Optional, Union

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    status,
)
from fastapi.routing import APIRoute

from app.api.dependencies import (
    get_exercise_service,
    get_user_service,
)
from app.api.errors import NotFoundError
from app.api.schemas.answer import (
    ChooseSentenceAnswerSchema,
    FillInTheBlankAnswerSchema,
)
from app.api.schemas.validation_result import ValidationResultSchema
from app.core.entities.exercise import Exercise
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.value_objects.answer import (
    create_answer_model_validate,
)

logger = logging.getLogger(__name__)
router = APIRouter(route_class=APIRoute)


@router.post(
    '/validate/',
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
        Union[
            FillInTheBlankAnswerSchema,
            ChooseSentenceAnswerSchema,
        ],
        Body(description="User's answer"),
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

        user_answer = create_answer_model_validate(answer.model_dump())

        exercise_attempt = await exercise_service.validate_exercise_attempt(
            user=user,
            exercise=exercise,
            answer=user_answer,
        )

        if exercise_attempt.is_correct is None:
            raise ValueError('Exercise attempt is_correct must not be None')

        logger.debug(f'{exercise_attempt=}')

        return ValidationResultSchema(
            is_correct=exercise_attempt.is_correct,
            feedback=exercise_attempt.feedback,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e
