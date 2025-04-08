from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.metrics import update_user_sessions_metrics

pytestmark = pytest.mark.asyncio


@pytest.fixture
def user_data():
    now = datetime.now(timezone.utc)
    return [
        dict(
            user_id=1,
            telegram_id='123',
            username='testuser1',
            name='Test User with frozen session',
            user_language='en',
            target_language='bg',
            language_level='A2',
            cohort='None',
            plan='None',
            last_exercise_at=now - timedelta(minutes=3),
            session_started_at=now - timedelta(minutes=7),
            exercises_get_in_session=15,
            session_frozen_until=now + timedelta(hours=3),
        ),
        dict(
            user_id=2,
            telegram_id='456',
            username='testuser2',
            name='Test User quited',
            user_language='en',
            target_language='bg',
            language_level='A2',
            cohort='None',
            plan='None',
            last_exercise_at=now - timedelta(minutes=10),
            session_started_at=now - timedelta(minutes=12),
            exercises_get_in_session=5,
        ),
        dict(
            user_id=2,
            telegram_id='456',
            username='testuser2',
            name='Test User Active',
            user_language='en',
            target_language='bg',
            language_level='A2',
            cohort='None',
            plan='None',
            last_exercise_at=now - timedelta(minutes=1),
            session_started_at=now - timedelta(minutes=3),
            exercises_get_in_session=7,
        ),
    ]


@pytest.fixture
def mock_backend_user_metrics():
    metrics = {
        'session_length': MagicMock(),
        'exercises_per_session': MagicMock(),
        'active': MagicMock(),
    }
    with patch('app.metrics.BACKEND_USER_METRICS', metrics):
        yield metrics


@patch('app.metrics.SQLAlchemyUserRepository')
async def test_update_user_sessions_metrics_patched(
    mock_repo_cls, mock_backend_user_metrics, user_data
):
    from app.core.entities.user import User

    mock_repo = AsyncMock()
    mock_repo.get_users_with_exercise_lately.return_value = [
        User(**u) for u in user_data
    ]
    mock_repo_cls.return_value = mock_repo

    # Act
    await update_user_sessions_metrics()

    # Assertions
    labels = {
        'cohort': 'None',
        'plan': 'None',
        'target_language': 'bg',
        'user_language': 'en',
        'language_level': 'A2',
    }

    session_lengths = [240.0, 120.0]
    exercises = [15, 5]

    session_length_metric = mock_backend_user_metrics['session_length']
    session_length_metric.labels.assert_called_with(**labels)
    session_length_metric.labels().observe.assert_has_calls(
        [call(s) for s in session_lengths], any_order=False
    )

    exercises_per_session_metric = mock_backend_user_metrics[
        'exercises_per_session'
    ]
    exercises_per_session_metric.labels.assert_called_with(**labels)
    exercises_per_session_metric.labels().inc.assert_has_calls(
        [call(e) for e in exercises], any_order=True
    )

    active_metric = mock_backend_user_metrics['active']
    active_metric.labels.assert_called_with(**labels)
    active_metric.labels().set.assert_called_once_with(1)
