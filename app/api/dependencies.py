from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.db.db import get_async_session
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.llm.llm_service import LLMService
from app.llm.llm_translator import LLMTranslator


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserService:
    return UserService(SQLAlchemyUserRepository(session))


def get_user_bot_profile_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserBotProfileService:
    return UserBotProfileService(SQLAlchemyUserBotProfileRepository(session))


def get_exercise_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ExerciseService:
    return ExerciseService(
        exercise_repository=SQLAlchemyExerciseRepository(session),
        exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
            session
        ),
        exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
            session
        ),
        llm_service=LLMService(),
        translator=LLMTranslator(),
    )


def get_user_progress_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserProgressService:
    return UserProgressService(
        user_service=UserService(SQLAlchemyUserRepository(session)),
        user_bot_profile_service=UserBotProfileService(
            SQLAlchemyUserBotProfileRepository(session)
        ),
        exercise_service=ExerciseService(
            exercise_repository=SQLAlchemyExerciseRepository(session),
            exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
                session
            ),
            exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
                session
            ),
            llm_service=LLMService(),
            translator=LLMTranslator(),
        ),
    )
