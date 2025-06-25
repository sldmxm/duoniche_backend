from unittest.mock import mock_open, patch

import pytest

from app.core.generation.config import ExerciseTopic
from app.core.services.language_config import LanguageConfigService


@pytest.fixture(autouse=True)
def clear_singleton():
    """Reset singleton before each test to ensure isolation."""
    LanguageConfigService._instance = None
    yield
    LanguageConfigService._instance = None


def test_singleton_pattern():
    """Test that LanguageConfigService is a singleton."""
    with (
        patch('pathlib.Path.exists', return_value=True),
        patch('builtins.open', mock_open(read_data='{}')),
    ):
        instance1 = LanguageConfigService()
        instance2 = LanguageConfigService()
        assert instance1 is instance2


@patch('pathlib.Path.exists', return_value=True)
@patch(
    'builtins.open',
    new_callable=mock_open,
    read_data="""
Bulgarian:
  bot_id: "Bulgarian"
  language_code: "bg"
  topics_exclude_from_generation:
    - "tech"
Serbian:
  bot_id: "Serbian"
  language_code: "sr"
""",
)
def test_load_config_success(mock_file, mock_exists):
    """Test successful loading and parsing of the YAML config."""
    service = LanguageConfigService()
    assert service.get_all_bot_ids() == ['Bulgarian', 'Serbian']
    assert service.get_config('Bulgarian')['language_code'] == 'bg'
    assert service.get_language_code('Serbian') == 'sr'
    assert service.get_config('German') is None
    excluded_topics = service.get_topics_excluded_from_generation('Bulgarian')
    assert excluded_topics == [ExerciseTopic.TECH]
    assert service.get_topics_excluded_from_generation('Serbian') is None
