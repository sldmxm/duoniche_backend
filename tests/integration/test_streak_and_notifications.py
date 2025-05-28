from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.core.entities.user_bot_profile import (
    BotID,
    UserStatusInBot,
)
from app.core.enums import LanguageLevel
from app.db.models import DBUserBotProfile
from app.db.models import User as DBUser
from app.workers.metrics_updater import (
    update_user_sessions_metrics,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_user_bot_profiles_data():
    now = datetime.now(timezone.utc)
    return [
        (
            {
                'user_id': 1,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.A2,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=3),
                'session_started_at': now - timedelta(minutes=7),
                'exercises_get_in_session': 15,
                'session_frozen_until': now - timedelta(hours=1),
                'exercises_get_in_set': 0,
                'errors_count_in_set': 0,
                'current_streak_days': 10,
                'wants_session_reminders': True,
                'last_long_break_reminder_type_sent': None,
                'last_long_break_reminder_sent_at': None,
            },
            {
                'user_id': 1,
                'telegram_id': '123',
                'username': 'user1_frozen',
                'name': 'User Frozen',
                'cohort': 'cohort_A',
                'plan': 'free',
            },
        ),
        (
            {
                'user_id': 2,
                'bot_id': BotID.BG,
                'user_language': 'ru',
                'language_level': LanguageLevel.B1,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now
                - (
                    settings.session_ttl_since_last_exercise
                    + timedelta(seconds=60)
                ),
                'session_started_at': now
                - (
                    settings.session_ttl_since_last_exercise
                    + timedelta(seconds=(60 + 120))
                ),
                'exercises_get_in_session': 5,
                'session_frozen_until': None,
                'exercises_get_in_set': 0,
                'errors_count_in_set': 0,
                'current_streak_days': 5,
                'wants_session_reminders': False,
                'last_long_break_reminder_type_sent': '1d',
                'last_long_break_reminder_sent_at': now
                - timedelta(days=1, hours=1),
            },
            {
                'user_id': 2,
                'telegram_id': '456',
                'username': 'user2_timeout',
                'name': 'User Timeout',
                'cohort': 'cohort_B',
                'plan': 'premium',
            },
        ),
        (
            {
                'user_id': 3,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.C1,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=1),
                'session_started_at': now - timedelta(minutes=3),
                'exercises_get_in_session': 7,
                'session_frozen_until': None,
                'exercises_get_in_set': 2,
                'errors_count_in_set': 1,
                'current_streak_days': 3,
                'wants_session_reminders': True,
                'last_long_break_reminder_type_sent': None,
                'last_long_break_reminder_sent_at': None,
            },
            {
                'user_id': 3,
                'telegram_id': '789',
                'username': 'user3_active',
                'name': 'User Active',
                'cohort': 'cohort_A',
                'plan': 'free',
            },
        ),
        (
            {
                'user_id': 4,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.C1,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=2),
                'session_started_at': now - timedelta(minutes=5),
                'exercises_get_in_session': 3,
                'session_frozen_until': None,
                'exercises_get_in_set': 3,
                'errors_count_in_set': 0,
                'current_streak_days': 3,
                'wants_session_reminders': True,
                'last_long_break_reminder_type_sent': None,
                'last_long_break_reminder_sent_at': None,
            },
            {
                'user_id': 4,
                'telegram_id': '101',
                'username': 'user4_active_same_labels',
                'name': 'User Active Same Labels',
                'cohort': 'cohort_A',
                'plan': 'free',
            },
        ),
    ]


@pytest.fixture
def mock_backend_user_metrics():
    # Define the expected structure and methods for each metric
    metrics_config = {
        'session_length': {
            'spec': ['labels', 'observe'],
            'methods': ['observe'],
        },
        'exercises_per_session': {
            'spec': ['labels', 'inc'],
            'methods': ['inc'],
        },
        'active': {'spec': ['labels', 'set'], 'methods': ['set']},
        'full_sessions': {'spec': ['labels', 'inc'], 'methods': ['inc']},
    }

    mocked_metrics_dict = {}
    for name, config in metrics_config.items():
        metric_mock = MagicMock(spec=config['spec'])
        labels_return_mock = MagicMock()
        for method_name in config['methods']:
            setattr(labels_return_mock, method_name, MagicMock())
        metric_mock.labels.return_value = labels_return_mock
        mocked_metrics_dict[name] = metric_mock

    with patch(
        'app.workers.metrics_updater.BACKEND_USER_METRICS', mocked_metrics_dict
    ):
        yield mocked_metrics_dict


@patch('app.workers.metrics_updater.SQLAlchemyUserBotProfileRepository')
async def test_update_user_sessions_metrics_new_logic(
    mock_repo_cls, mock_backend_user_metrics, mock_user_bot_profiles_data
):
    mock_repo_instance = AsyncMock()

    processed_profiles = []
    for profile_data, user_data_dict in mock_user_bot_profiles_data:
        user_obj_data = {
            k: user_data_dict[k]
            for k in [
                'user_id',
                'telegram_id',
                'username',
                'name',
                'cohort',
                'plan',
            ]
            if k in user_data_dict
        }
        user_obj = DBUser(**user_obj_data)
        profile_obj = DBUserBotProfile(**profile_data)
        profile_obj.user = user_obj
        processed_profiles.append(profile_obj)

    mock_repo_instance.get_by_recent_exercise_with_user_data.return_value = (
        processed_profiles
    )
    mock_repo_cls.return_value = mock_repo_instance

    await update_user_sessions_metrics()

    session_length_metric = mock_backend_user_metrics['session_length']
    exercises_per_session_metric = mock_backend_user_metrics[
        'exercises_per_session'
    ]
    active_metric = mock_backend_user_metrics['active']

    labels_user1 = {
        'cohort': 'cohort_A',
        'plan': 'free',
        'target_language': BotID.BG.value,
        'user_language': 'en',
        'language_level': LanguageLevel.A2.value,
    }

    labels_user2 = {
        'cohort': 'cohort_B',
        'plan': 'premium',
        'target_language': BotID.BG.value,
        'user_language': 'ru',
        'language_level': LanguageLevel.B1.value,
    }

    # Assertions for session_length metric (Users 1 and 2)
    session_length_metric.labels.assert_any_call(**labels_user1)
    session_length_metric.labels().observe.assert_any_call(240.0)

    session_length_metric.labels.assert_any_call(**labels_user2)
    session_length_metric.labels().observe.assert_any_call(
        120.0
    )  # Corrected: duration is 120s

    assert session_length_metric.labels().observe.call_count == 2

    # Assertions for exercises_per_session metric (Users 1 and 2)
    exercises_per_session_metric.labels.assert_any_call(**labels_user1)
    exercises_per_session_metric.labels().inc.assert_any_call(15)

    exercises_per_session_metric.labels.assert_any_call(**labels_user2)
    exercises_per_session_metric.labels().inc.assert_any_call(5)

    assert exercises_per_session_metric.labels().inc.call_count == 2

    full_sessions_metric = mock_backend_user_metrics['full_sessions']
    assert full_sessions_metric.labels().inc.call_count == 0

    labels_active_users_group = {
        'cohort': 'cohort_A',
        'plan': 'free',
        'target_language': BotID.BG.value,
        'user_language': 'en',
        'language_level': LanguageLevel.C1.value,
    }

    # Assertions for 'active' metric
    active_metric.labels.assert_any_call(**labels_user1)
    active_metric.labels.assert_any_call(**labels_user2)
    active_metric.labels.assert_any_call(**labels_active_users_group)

    # Check the values passed to set()
    # This assumes that for each .labels() call, the .set()
    # on the returned mock is called.
    active_labels_return_mock = active_metric.labels.return_value
    set_call_values = [
        call_args[0][0]
        for call_args in active_labels_return_mock.set.call_args_list
    ]

    assert (
        set_call_values.count(0) == 2
    )  # For user1 and user2 (sessions ended)
    assert (
        set_call_values.count(2) == 1
    )  # For the group of user3 and user4 (active)
    assert len(set_call_values) == 3

    mock_repo_instance.get_by_recent_exercise_with_user_data.assert_awaited_once()
    call_args = (
        mock_repo_instance.get_by_recent_exercise_with_user_data.call_args
    )
    assert 'period_seconds' in call_args.kwargs
