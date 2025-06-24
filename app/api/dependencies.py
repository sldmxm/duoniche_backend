from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Depends, Request
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.async_task_cache import AsyncTaskCache
from app.core.services.exercise import ExerciseService
from app.core.services.language_config import LanguageConfigService
from app.core.services.payment import PaymentService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.services.user_report import UserReportService
from app.core.services.user_settings import UserSettingsService
from app.db.db import get_async_session
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.payment import SQLAlchemyPaymentRepository
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.db.repositories.user_report import SQLAlchemyUserReportRepository
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


async def get_language_config_service(
    request: Request,
) -> LanguageConfigService:
    if not hasattr(request.app.state, 'language_config_service'):
        raise RuntimeError(
            'LanguageConfigService not initialized in app.state'
        )
    return request.app.state.language_config_service


async def get_redis_dependency(request: Request) -> AsyncRedis:
    if not hasattr(request.app.state, 'redis_client'):
        raise RuntimeError('Redis client not initialized in app.state')
    return request.app.state.redis_client


async def get_arq_pool(request: Request) -> ArqRedis:
    if not hasattr(request.app.state, 'arq_pool'):
        raise RuntimeError('ARQ pool not initialized in app.state')
    return request.app.state.arq_pool


def get_user_settings_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    redis_client: Annotated[AsyncRedis, Depends(get_redis_dependency)],
    language_config_service: Annotated[
        LanguageConfigService, Depends(get_language_config_service)
    ],
) -> UserSettingsService:
    """Dependency to get the user settings service."""
    return UserSettingsService(
        user_service=user_service,
        user_bot_profile_service=user_bot_profile_service,
        redis_client=redis_client,
        language_config_service=language_config_service,
    )


async def get_async_task_cache_dependency(
    request: Request,
) -> AsyncTaskCache:
    if not hasattr(request.app.state, 'async_task_cache'):
        raise RuntimeError('AsyncTaskCache not initialized in app.state')
    return request.app.state.async_task_cache


async def get_llm_service_dependency(request: Request) -> LLMService:
    if not hasattr(request.app.state, 'llm_service'):
        raise RuntimeError('LLMService not initialized in app.state')
    return request.app.state.llm_service


async def get_translator_dependency(request: Request) -> LLMTranslator:
    if not hasattr(request.app.state, 'translator'):
        raise RuntimeError('LLMTranslator not initialized in app.state')
    return request.app.state.translator


def get_exercise_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    async_task_cache: Annotated[
        AsyncTaskCache, Depends(get_async_task_cache_dependency)
    ],
    llm_service: Annotated[LLMService, Depends(get_llm_service_dependency)],
    translator: Annotated[LLMTranslator, Depends(get_translator_dependency)],
) -> ExerciseService:
    return ExerciseService(
        exercise_repository=SQLAlchemyExerciseRepository(session),
        exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
            session
        ),
        exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
            session
        ),
        llm_service=llm_service,
        translator=translator,
        async_task_cache=async_task_cache,
    )


def get_user_report_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
    llm_service: Annotated[LLMService, Depends(get_llm_service_dependency)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
) -> UserReportService:
    """
    Dependency to get the UserReportService.
    """
    return UserReportService(
        user_report_repository=SQLAlchemyUserReportRepository(session),
        exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
            session
        ),
        arq_pool=arq_pool,
        llm_service=llm_service,
        user_bot_profile_service=user_bot_profile_service,
    )


def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_report_service: Annotated[
        UserReportService, Depends(get_user_report_service)
    ],
) -> PaymentService:
    """Dependency to get the payment service."""
    return PaymentService(
        payment_repository=SQLAlchemyPaymentRepository(session),
        user_bot_profile_service=user_bot_profile_service,
        user_report_service=user_report_service,
    )


def get_user_progress_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    exercise_service: Annotated[
        ExerciseService, Depends(get_exercise_service)
    ],
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    user_settings_service: Annotated[
        UserSettingsService, Depends(get_user_settings_service)
    ],
) -> UserProgressService:
    return UserProgressService(
        user_service=user_service,
        user_bot_profile_service=user_bot_profile_service,
        exercise_service=exercise_service,
        payment_service=payment_service,
        user_settings_service=user_settings_service,
    )
