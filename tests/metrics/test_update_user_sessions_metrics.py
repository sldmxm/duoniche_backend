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
            {  # User 1: Session completed due to past freeze
                'user_id': 1,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.A2,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=3),
                'session_started_at': now - timedelta(minutes=7),
                'exercises_get_in_session': 15,
                'session_frozen_until': now - timedelta(hours=1),
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
            {  # User 2: Session completed due to timeout
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
            {  # User 3: Active session
                'user_id': 3,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.C1,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=1),
                'session_started_at': now - timedelta(minutes=3),
                'exercises_get_in_session': 7,
                'session_frozen_until': None,
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
            {  # User 4: Active session, same labels as User 3
                'user_id': 4,
                'bot_id': BotID.BG,
                'user_language': 'en',
                'language_level': LanguageLevel.C1,
                'status': UserStatusInBot.ACTIVE,
                'last_exercise_at': now - timedelta(minutes=2),
                'session_started_at': now - timedelta(minutes=5),
                'exercises_get_in_session': 3,
                'session_frozen_until': None,
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
    metrics = {
        'session_length': MagicMock(spec=['labels', 'observe']),
        'exercises_per_session': MagicMock(spec=['labels', 'inc']),
        'active': MagicMock(spec=['labels', 'set']),
    }
    for metric_mock in metrics.values():
        metric_mock.labels.return_value = metric_mock

    with patch('app.workers.metrics_updater.BACKEND_USER_METRICS', metrics):
        yield metrics


@patch('app.workers.metrics_updater.SQLAlchemyUserBotProfileRepository')
async def test_update_user_sessions_metrics_new_logic(
    mock_repo_cls, mock_backend_user_metrics, mock_user_bot_profiles_data
):
    mock_repo_instance = AsyncMock()

    processed_profiles = []
    for profile_data, user_data_dict in mock_user_bot_profiles_data:
        user_obj = DBUser(**user_data_dict)
        profile_obj = DBUserBotProfile(**profile_data)
        profile_obj.user = user_obj
        processed_profiles.append(profile_obj)

    mock_repo_instance.get_by_recent_exercise_with_user_data.return_value = (
        processed_profiles
    )
    mock_repo_cls.return_value = mock_repo_instance

    # Act
    await update_user_sessions_metrics()

    # Assertions
    session_length_metric = mock_backend_user_metrics['session_length']
    exercises_per_session_metric = mock_backend_user_metrics[
        'exercises_per_session'
    ]
    active_metric = mock_backend_user_metrics['active']

    # Labels for User 1 (completed session)
    labels_user1 = {
        'cohort': 'cohort_A',
        'plan': 'free',
        'target_language': BotID.BG.value,
        'user_language': 'en',
        'language_level': LanguageLevel.A2.value,
    }

    # Labels for User 2 (completed session)
    labels_user2 = {
        'cohort': 'cohort_B',
        'plan': 'premium',
        'target_language': BotID.BG.value,
        'user_language': 'ru',
        'language_level': LanguageLevel.B1.value,
    }

    # Assertions for session_length metric (Users 1 and 2)
    print(session_length_metric.labels.call_args_list)
    print(session_length_metric.observe.call_args_list)

    session_length_metric.labels.assert_any_call(**labels_user1)
    session_length_metric.labels.assert_any_call(**labels_user2)

    observe_calls = [
        c.args[0] for c in session_length_metric.observe.call_args_list
    ]
    assert 240.0 in observe_calls
    assert 120.0 in observe_calls
    assert len(observe_calls) == 2

    # Assertions for exercises_per_session metric (Users 1 and 2)
    exercises_per_session_metric.labels.assert_any_call(**labels_user1)
    exercises_per_session_metric.labels.assert_any_call(**labels_user2)

    inc_calls_args = [
        c.args[0] for c in exercises_per_session_metric.inc.call_args_list
    ]
    assert 15 in inc_calls_args  # User 1
    assert 5 in inc_calls_args  # User 2
    assert len(inc_calls_args) == 2

    # Labels for active users (Users 3 and 4 have the same labels)
    labels_active_users_group = {
        'cohort': 'cohort_A',
        'plan': 'free',
        'target_language': BotID.BG.value,
        'user_language': 'en',
        'language_level': LanguageLevel.C1.value,
    }

    # Assertions for 'active' metric
    # Expect:
    # - labels_user1 set to 0
    # - labels_user2 set to 0
    # - labels_active_users_group set to 2 (for users 3 and 4)

    # Check that labels() was called for all relevant groups
    active_metric.labels.assert_any_call(**labels_user1)
    active_metric.labels.assert_any_call(**labels_user2)
    active_metric.labels.assert_any_call(**labels_active_users_group)

    set_values_for_labels = {}
    for i in range(len(active_metric.labels.call_args_list)):
        label_call_kwargs = active_metric.labels.call_args_list[i].kwargs
        set_value = active_metric.set.call_args_list[i].args[0]
        label_key = frozenset(label_call_kwargs.items())
        set_values_for_labels[label_key] = set_value

    assert set_values_for_labels.get(frozenset(labels_user1.items())) == 0
    assert set_values_for_labels.get(frozenset(labels_user2.items())) == 0
    assert (
        set_values_for_labels.get(frozenset(labels_active_users_group.items()))
        == 2
    )

    # Verify repository call
    mock_repo_instance.get_by_recent_exercise_with_user_data.assert_awaited_once()
    call_args = (
        mock_repo_instance.get_by_recent_exercise_with_user_data.call_args
    )
    assert 'period_seconds' in call_args.kwargs
