from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.core.entities.user_bot_profile import UserBotProfile
from app.core.enums import ExerciseType, LanguageLevel, ReportStatus
from app.core.generation.config import ExerciseTopic
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_report import (
    MIN_ATTEMPTS_FOR_WEEKLY_REPORT,
    ReportNotFoundError,
    UserReportService,
)
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.db.models import DBUserBotProfile
from app.db.models import User as DBUser
from app.db.models.exercise import Exercise as ExerciseModel
from app.db.models.exercise_attempt import (
    ExerciseAttempt as ExerciseAttemptModel,
)
from app.db.models.user_report import UserReport as UserReportModel
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.db.repositories.user_report import SQLAlchemyUserReportRepository
from app.llm.llm_service import LLMService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope='function')
async def service_db_session(
    async_session_maker,
) -> AsyncGenerator[AsyncSession, Any]:
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def fill_sample_exercises(
    service_db_session: AsyncSession,
) -> AsyncGenerator[list[ExerciseModel], Any]:
    exercises = [
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.A1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='I ____ to the store yesterday.',
                words=['went'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='Bulgarian',
            language_level=LanguageLevel.A2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Тя ____ от три часа.',
                words=['учи'],
            ).model_dump(),
        ),
    ]
    service_db_session.add_all(exercises)
    await service_db_session.commit()
    yield exercises


@pytest.fixture
def fixed_test_time():
    return datetime(2025, 6, 23, 12, 0, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def active_user_with_attempts(
    service_db_session: AsyncSession,
    user_data,
    user_bot_profile_data,
    fill_sample_exercises,
    fixed_test_time,
):
    user = DBUser(**user_data)
    service_db_session.add(user)
    await service_db_session.flush()

    profile = DBUserBotProfile(
        **user_bot_profile_data,
        last_exercise_at=fixed_test_time - timedelta(days=1),
    )
    service_db_session.add(profile)
    await service_db_session.flush()

    bulgarian_exercise = next(
        ex
        for ex in fill_sample_exercises
        if ex.exercise_language == 'Bulgarian'
    )

    for _ in range(MIN_ATTEMPTS_FOR_WEEKLY_REPORT):
        attempt = ExerciseAttemptModel(
            user_id=user.user_id,
            exercise_id=bulgarian_exercise.exercise_id,
            is_correct=True,
            answer={},
            created_at=fixed_test_time - timedelta(days=2),
        )
        service_db_session.add(attempt)

    await service_db_session.commit()
    return User.model_validate(user), UserBotProfile.model_validate(profile)


@pytest_asyncio.fixture
async def inactive_user(
    service_db_session: AsyncSession,
    user_data,
    user_bot_profile_data,
    fixed_test_time,
):
    user_data = {**user_data, 'user_id': 54321, 'telegram_id': 'inactive'}
    user = DBUser(**user_data)
    service_db_session.add(user)
    await service_db_session.flush()

    profile_data = {
        **user_bot_profile_data,
        'user_id': user.user_id,
        'last_exercise_at': fixed_test_time - timedelta(days=8),
    }
    profile = DBUserBotProfile(**profile_data)
    service_db_session.add(profile)

    await service_db_session.commit()
    return User.model_validate(user), UserBotProfile.model_validate(profile)


@pytest_asyncio.fixture
async def user_with_few_attempts(
    service_db_session: AsyncSession,
    user_data,
    user_bot_profile_data,
    fill_sample_exercises,
    fixed_test_time,
):
    user_data = {**user_data, 'user_id': 98765, 'telegram_id': 'few_attempts'}
    user = DBUser(**user_data)
    service_db_session.add(user)
    await service_db_session.flush()

    profile_data = {
        **user_bot_profile_data,
        'user_id': user.user_id,
        'last_exercise_at': fixed_test_time - timedelta(days=1),
    }
    profile = DBUserBotProfile(**profile_data)
    service_db_session.add(profile)

    bulgarian_exercise = next(
        ex
        for ex in fill_sample_exercises
        if ex.exercise_language == 'Bulgarian'
    )

    attempt = ExerciseAttemptModel(
        user_id=user.user_id,
        exercise_id=bulgarian_exercise.exercise_id,
        is_correct=True,
        answer={},
        created_at=fixed_test_time - timedelta(days=2),
    )
    service_db_session.add(attempt)

    await service_db_session.commit()
    return User.model_validate(user), UserBotProfile.model_validate(profile)


def create_user_report_service(
    session: AsyncSession, mock_http_client
) -> UserReportService:
    user_bot_profile_service = UserBotProfileService(
        SQLAlchemyUserBotProfileRepository(session)
    )
    return UserReportService(
        user_report_repository=SQLAlchemyUserReportRepository(session),
        exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
            session
        ),
        user_bot_profile_service=user_bot_profile_service,
        arq_pool=AsyncMock(spec=ArqRedis),
        llm_service=LLMService(http_client=mock_http_client),
    )


@patch('app.core.services.user_report.datetime')
async def test_generate_and_save_short_weekly_reports_for_active_user(
    mock_datetime,
    active_user_with_attempts,
    service_db_session: AsyncSession,
    fixed_test_time,
    mock_http_client,
):
    mock_datetime.now.return_value = fixed_test_time
    user, profile = active_user_with_attempts

    user_report_service = create_user_report_service(
        service_db_session, mock_http_client
    )

    reports_to_notify = (
        await user_report_service.generate_and_save_short_weekly_reports()
    )
    await service_db_session.commit()

    assert len(reports_to_notify) == 1
    notified_profile, notified_user, saved_report = reports_to_notify[0]

    assert notified_user.user_id == user.user_id
    assert notified_profile.user_id == profile.user_id

    db_report = await service_db_session.get(
        UserReportModel, saved_report.report_id
    )
    assert db_report is not None
    assert db_report.user_id == user.user_id
    assert 'Your progress this week' in db_report.short_report

    updated_profile = await service_db_session.get(
        DBUserBotProfile, (profile.user_id, profile.bot_id)
    )
    assert updated_profile.last_report_generated_at is not None


@patch('app.core.services.user_report.datetime')
async def test_generate_reports_skips_inactive_and_low_activity_users(
    mock_datetime,
    active_user_with_attempts,
    inactive_user,
    user_with_few_attempts,
    service_db_session: AsyncSession,
    fixed_test_time,
    mock_http_client,
):
    mock_datetime.now.return_value = fixed_test_time

    user_report_service = create_user_report_service(
        service_db_session, mock_http_client
    )

    reports_to_notify = (
        await user_report_service.generate_and_save_short_weekly_reports()
    )
    await service_db_session.commit()

    assert len(reports_to_notify) == 1
    assert (
        reports_to_notify[0][1].user_id == active_user_with_attempts[0].user_id
    )


async def test_request_detailed_report_enqueues_task(
    service_db_session: AsyncSession,
    active_user_with_attempts,
    mock_http_client,
):
    user, profile = active_user_with_attempts
    report = UserReportModel(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=date.today() - timedelta(days=7),
        short_report='Test',
        status=ReportStatus.PENDING.value,
    )
    service_db_session.add(report)
    await service_db_session.commit()

    user_report_service = create_user_report_service(
        service_db_session, mock_http_client
    )
    mock_arq_pool = AsyncMock(spec=ArqRedis)
    user_report_service.arq_pool = mock_arq_pool

    status = await user_report_service.request_detailed_report(profile)

    assert status == ReportStatus.GENERATING
    mock_arq_pool.enqueue_job.assert_awaited_once_with(
        'generate_and_send_detailed_report_arq',
        report.report_id,
    )


async def test_request_detailed_report_for_non_existent_report(
    service_db_session: AsyncSession,
    active_user_with_attempts,
    mock_http_client,
):
    user, profile = active_user_with_attempts
    user_report_service = create_user_report_service(
        service_db_session, mock_http_client
    )

    with pytest.raises(ReportNotFoundError):
        await user_report_service.request_detailed_report(profile)


async def test_generate_full_report_text(
    service_db_session: AsyncSession,
    active_user_with_attempts,
    fixed_test_time,
    mock_http_client,
):
    user, profile = active_user_with_attempts
    report = UserReportModel(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=fixed_test_time.date() - timedelta(days=7),
        short_report='Test',
    )
    service_db_session.add(report)
    await service_db_session.commit()

    user_report_service = create_user_report_service(
        service_db_session, mock_http_client
    )
    mock_llm_service = AsyncMock()
    mock_llm_service.generate_detailed_report_text.return_value = (
        'This is your detailed report.'
    )
    user_report_service.llm_service = mock_llm_service

    full_text = await user_report_service.generate_full_report_text(
        user_id=user.user_id, bot_id=profile.bot_id
    )

    assert full_text == 'This is your detailed report.'
    mock_llm_service.generate_detailed_report_text.assert_awaited_once()
    call_context = (
        mock_llm_service.generate_detailed_report_text.call_args.kwargs[
            'context'
        ]
    )
    assert 'current_summary' in call_context
    assert 'prev_summary' in call_context
    assert 'incorrect_attempts' in call_context
    assert (
        f'completed {MIN_ATTEMPTS_FOR_WEEKLY_REPORT} exercises'
        in call_context['current_summary']
    )
