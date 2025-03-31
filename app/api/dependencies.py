from typing import Any, AsyncGenerator

from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.db.db import get_async_session
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user import SQLAlchemyUserRepository
from app.llm.llm_service import LLMService
from app.translator.translator import Translator


async def get_exercise_service() -> AsyncGenerator[ExerciseService, Any]:
    async for session in get_async_session():
        yield ExerciseService(
            exercise_repository=SQLAlchemyExerciseRepository(session),
            exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
                session
            ),
            exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
                session
            ),
            llm_service=LLMService(),
            translator=Translator(),
        )


async def get_user_service() -> AsyncGenerator[UserService, Any]:
    async for session in get_async_session():
        yield UserService(SQLAlchemyUserRepository(session))
