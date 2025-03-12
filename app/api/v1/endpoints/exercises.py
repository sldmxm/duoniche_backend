from typing import Annotated

from fastapi import APIRouter, Depends, Query
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
from app.schemas.user import UserSchema
from app.schemas.validation_result import ValidationResultSchema

router = APIRouter(route_class=APIRoute)


@router.post(
    '/new',
    response_model=ExerciseSchema,
    response_model_exclude_none=True,
)
async def get_new_exercise(
    user: UserSchema,
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    language_level_query: Annotated[
        str | None, Query(description='Language level')
    ] = None,
    exercise_type_query: Annotated[
        ExerciseType | None, Query(description='Type of exercise')
    ] = None,
) -> ExerciseSchema:
    language_level = language_level_query or ''
    exercise_type = exercise_type_query or ExerciseType.FILL_IN_THE_BLANK
    exercise: Exercise | None = await exercise_service.get_new_exercise(
        User(**user.model_dump()), language_level, exercise_type.value
    )
    if not exercise:
        raise NotFoundError('Exercise not found')
    return ExerciseSchema.model_validate(exercise)


@router.post(
    '/validate',
    response_model=ValidationResultSchema,
    response_model_exclude_none=True,
)
async def validate_exercise_attempt(
    user: UserSchema,
    exercise_id_query: Annotated[int, Query(description='Exercise ID')],
    answer_query: Annotated[
        FillInTheBlankAnswerSchema, Query(description='Answer')
    ],
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
) -> ValidationResultSchema:
    exercise_id = exercise_id_query
    answer = answer_query
    exercise: Exercise | None = await exercise_service.get_exercise_by_id(
        exercise_id
    )
    if not exercise:
        raise NotFoundError('Exercise not found')

    exercise_attempt: ExerciseAttempt = (
        await exercise_service.validate_exercise_attempt(
            User(**user.model_dump()),
            exercise,
            FillInTheBlankAnswer(**answer.model_dump()),
        )
    )
    return ValidationResultSchema(
        is_correct=exercise_attempt.is_correct,
        feedback=exercise_attempt.feedback,
    )
