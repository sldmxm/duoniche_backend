from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import UserBotProfile
from app.core.enums import ExerciseType, LanguageLevel, ReportStatus
from app.core.generation.config import ExerciseTopic
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.db.models import DBUserBotProfile
from app.db.models import User as DBUser
from app.db.models.exercise import Exercise as ExerciseModel
from app.db.models.exercise_attempt import (
    ExerciseAttempt as ExerciseAttemptModel,
)
from app.db.models.user_report import UserReport
from app.db.models.user_report import UserReport as UserReportModel
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.workers.arq_tasks.reports import (
    generate_and_send_detailed_report_arq,
    run_report_generation_cycle_arq,
    send_detailed_report_notification_arq,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope='function')
async def worker_db_session(
    async_session_maker,
) -> AsyncGenerator[AsyncSession, Any]:
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def fill_sample_exercises(
    worker_db_session,
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
            exercise_language='en',
            language_level=LanguageLevel.A2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='She has been ____ for three hours.',
                words=['studying'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.B1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='If I ____ more time, I would help you.',
                words=['had'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.B2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='The issue ____ in the latest meeting.',
                words=['was addressed'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.C1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='The manuscript ____ to have '
                'been written in the 15th century.',
                words=['is believed'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='Bulgarian',
            language_level=LanguageLevel.A1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Аз ____ до магазина вчера.',
                words=['отидох'],
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
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='Bulgarian',
            language_level=LanguageLevel.B1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Ако ____ повече време, щях да ти помогна.',
                words=['имах'],
            ).model_dump(),
        ),
    ]

    worker_db_session.add_all(exercises)
    await worker_db_session.commit()
    yield exercises


@pytest.fixture
def fixed_test_time():
    return datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def add_user_with_active_attempts(
    worker_db_session,
    user_data,
    user_bot_profile_data,
    fill_sample_exercises,
    fixed_test_time,
) -> tuple[DBUser, DBUserBotProfile]:
    now = fixed_test_time
    bulgarian_exercises = [
        ex
        for ex in fill_sample_exercises
        if ex.exercise_language == 'Bulgarian'
    ]

    user = DBUser(**user_data)
    worker_db_session.add(user)
    await worker_db_session.flush()
    profile = DBUserBotProfile(
        **user_bot_profile_data,
        last_exercise_at=now - timedelta(days=1),
    )
    worker_db_session.add(profile)
    await worker_db_session.flush()

    for i in range(15):
        worker_db_session.add(
            ExerciseAttemptModel(
                user_id=user.user_id,
                exercise_id=bulgarian_exercises[
                    i % len(bulgarian_exercises)
                ].exercise_id,
                answer={'type': 'test'},
                is_correct=i % 2 == 0,
                created_at=now - timedelta(days=(i % 5) + 1, seconds=1),
            )
        )
    await worker_db_session.commit()

    return user, profile


@pytest_asyncio.fixture
async def add_user_with_short_report(
    worker_db_session,
    user_data,
    user_bot_profile_data,
) -> tuple[DBUser, DBUserBotProfile, UserReportModel]:
    user = DBUser(**user_data)
    worker_db_session.add(user)
    await worker_db_session.flush()
    profile = DBUserBotProfile(
        **user_bot_profile_data,
    )
    worker_db_session.add(profile)
    await worker_db_session.flush()
    report = UserReportModel(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=datetime.now(timezone.utc).date()
        - timedelta(
            days=7,
        ),
        short_report='Your weekly summary.',
        status=ReportStatus.PENDING.value,
    )
    worker_db_session.add(report)
    await worker_db_session.commit()
    await worker_db_session.refresh(user)
    await worker_db_session.refresh(profile)
    await worker_db_session.refresh(report)
    return user, profile, report


@pytest_asyncio.fixture
async def add_user_with_generated_report(
    worker_db_session,
    user_data,
    user_bot_profile_data,
) -> tuple[DBUser, DBUserBotProfile, UserReportModel]:
    user = DBUser(**user_data)
    worker_db_session.add(user)
    await worker_db_session.flush()
    profile = DBUserBotProfile(
        **user_bot_profile_data,
    )
    worker_db_session.add(profile)
    await worker_db_session.flush()
    report = UserReportModel(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=datetime.now(timezone.utc).date()
        - timedelta(
            days=7,
        ),
        short_report='Your weekly summary.',
        full_report='Your detailed weekly summary.',
        status=ReportStatus.GENERATED.value,
    )
    worker_db_session.add(report)
    await worker_db_session.commit()
    await worker_db_session.refresh(user)
    await worker_db_session.refresh(profile)
    await worker_db_session.refresh(report)
    return user, profile, report


@pytest_asyncio.fixture(scope='function')
async def worker_user_bot_profile_service(worker_db_session):
    return UserBotProfileService(
        profile_repo=SQLAlchemyUserBotProfileRepository(worker_db_session)
    )


async def test_get_period_summary_for_user_and_bot(
    worker_db_session,
    user_data,
    user_bot_profile_data,
    fill_sample_exercises,
):
    user = DBUser(**user_data)
    worker_db_session.add(user)
    await worker_db_session.flush()

    profile = DBUserBotProfile(**user_bot_profile_data)
    worker_db_session.add(profile)
    await worker_db_session.flush()

    now = datetime.now(timezone.utc)
    bg_exercises = [
        ex
        for ex in fill_sample_exercises
        if ex.exercise_language == 'Bulgarian'
    ]

    bg_exercises[0].grammar_tags = {
        'grammar': ['verb tense: present'],
        'vocabulary': ['general'],
    }
    bg_exercises[1].grammar_tags = {
        'grammar': ['verb tense: present'],
        'vocabulary': ['food'],
    }
    bg_exercises[2].grammar_tags = {
        'grammar': ['modal verbs'],
        'vocabulary': ['travel'],
    }

    worker_db_session.add_all(
        [bg_exercises[0], bg_exercises[1], bg_exercises[2]]
    )
    await worker_db_session.flush()

    attempts_data = [
        {
            'user_id': user.user_id,
            'exercise_id': bg_exercises[0].exercise_id,
            'answer': {'type': 'test'},
            'is_correct': True,
            'created_at': now - timedelta(days=1),
            'error_tags': None,
        },
        {
            'user_id': user.user_id,
            'exercise_id': bg_exercises[1].exercise_id,
            'answer': {'type': 'test'},
            'is_correct': True,
            'created_at': now - timedelta(days=2),
            'error_tags': None,
        },
        {
            'user_id': user.user_id,
            'exercise_id': bg_exercises[2].exercise_id,
            'answer': {'type': 'test'},
            'is_correct': False,
            'created_at': now - timedelta(days=3),
            'error_tags': {
                'grammar': ['verb tense: past'],
                'vocabulary': ['travel'],
            },
        },
        {
            'user_id': user.user_id,
            'exercise_id': bg_exercises[0].exercise_id,
            'answer': {'type': 'test'},
            'is_correct': True,
            'created_at': now - timedelta(days=8),
            'error_tags': None,
        },
    ]

    for attempt in attempts_data:
        worker_db_session.add(ExerciseAttemptModel(**attempt))
    await worker_db_session.commit()

    repo = SQLAlchemyExerciseAttemptRepository(worker_db_session)
    summary = await repo.get_period_summary_for_user_and_bot(
        user_id=user.user_id,
        bot_id=profile.bot_id,
        start_date=now - timedelta(days=7),
        end_date=now,
    )

    assert summary['total_attempts'] == 3
    assert summary['correct_attempts'] == 2
    assert summary['active_days'] == 3
    assert summary['grammar_tags'] == {
        'verb tense: present': 2,
        'modal verbs': 1,
    }
    assert summary['vocab_tags'] == {'general': 1, 'food': 1, 'travel': 1}
    assert summary['error_grammar_tags'] == {'verb tense: past': 1}
    assert summary['error_vocab_tags'] == {'travel': 1}


@patch('app.workers.arq_tasks.reports.NotificationProducerService')
@patch('app.workers.arq_tasks.reports.UserReportService')
async def test_run_report_generation_cycle_arq(
    mock_report_service_cls,
    mock_notification_producer_cls,
    add_user_with_active_attempts,
):
    user, profile = add_user_with_active_attempts

    mock_report_service = AsyncMock()
    mock_report_service_cls.return_value = mock_report_service

    mock_producer = AsyncMock()
    mock_notification_producer_cls.return_value = mock_producer

    report = UserReport(
        report_id=1,
        user_id=user.user_id,
        bot_id=profile.bot_id,
        week_start_date=datetime.now(timezone.utc).date() - timedelta(days=7),
        short_report='Your progress this week...',
        status=ReportStatus.PENDING,
        generated_at=datetime.now(timezone.utc),
    )
    mock_report_service.generate_and_save_short_weekly_reports.return_value = [
        (
            UserBotProfile.model_validate(profile),
            User.model_validate(user),
            report,
        )
    ]

    ctx = {'arq_pool': AsyncMock(spec=ArqRedis), 'llm_service': AsyncMock()}

    await run_report_generation_cycle_arq(ctx)

    mock_report_service.generate_and_save_short_weekly_reports.assert_awaited_once()

    mock_producer.enqueue_weekly_report_notification.assert_awaited_once()

    call_args = (
        mock_producer.enqueue_weekly_report_notification.call_args.kwargs
    )
    assert isinstance(call_args['user'], User)
    assert isinstance(call_args['profile'], UserBotProfile)
    assert call_args['user'].user_id == user.user_id
    assert call_args['report'].report_id == report.report_id


@patch('app.workers.arq_tasks.reports.async_session_maker')
async def test_generate_and_send_detailed_report_arq(
    mock_async_session_maker,
    worker_db_session,
    add_user_with_short_report,
):
    user, profile, report = add_user_with_short_report
    mock_async_session_maker.return_value = AsyncMock()
    mock_async_session_maker.return_value.__aenter__.return_value = (
        worker_db_session
    )
    mock_async_session_maker.return_value.__aexit__.return_value = None

    mock_llm_service = AsyncMock()
    mock_llm_service.generate_detailed_report_text.return_value = (
        'Detailed report text.'
    )

    mock_arq_pool = AsyncMock(spec=ArqRedis)
    mock_arq_pool.enqueue_job = AsyncMock()

    ctx = {'llm_service': mock_llm_service, 'arq_pool': mock_arq_pool}

    await generate_and_send_detailed_report_arq(ctx, report.report_id)

    await worker_db_session.refresh(report)
    assert report.full_report == 'Detailed report text.'
    assert report.status == ReportStatus.GENERATED.value

    mock_llm_service.generate_detailed_report_text.assert_awaited_once()
    mock_arq_pool.enqueue_job.assert_awaited_once_with(
        'send_detailed_report_notification_arq',
        report.report_id,
        _defer_by=timedelta(seconds=settings.full_weekly_report_sending_delay),
    )


@patch('app.workers.arq_tasks.reports.NotificationProducerService')
@patch('app.workers.arq_tasks.reports.async_session_maker')
async def test_send_detailed_report_notification_arq(
    mock_async_session_maker,
    mock_notification_producer_cls,
    worker_db_session,
    add_user_with_generated_report,
):
    user, profile, report = add_user_with_generated_report
    mock_async_session_maker.return_value = AsyncMock()
    mock_async_session_maker.return_value.__aenter__.return_value = (
        worker_db_session
    )
    mock_async_session_maker.return_value.__aexit__.return_value = None

    mock_producer = AsyncMock()
    mock_producer.enqueue_detailed_report_notification.return_value = True
    mock_notification_producer_cls.return_value = mock_producer

    ctx = {}

    await send_detailed_report_notification_arq(ctx, report.report_id)

    await worker_db_session.refresh(report)
    assert report.status == ReportStatus.SENT.value

    mock_producer.enqueue_detailed_report_notification.assert_awaited_once()
    call_args = (
        mock_producer.enqueue_detailed_report_notification.call_args.kwargs
    )
    assert isinstance(call_args['user'], User)
    assert call_args['user'].user_id == user.user_id
    assert isinstance(call_args['profile'], UserBotProfile)
    assert call_args['profile'].user_id == profile.user_id
    assert call_args['report'].report_id == report.report_id
