import json
from datetime import timedelta
from typing import Dict, List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import LanguageLevel


class Settings(BaseSettings):  # type: ignore
    debug: bool = False

    postgres_user: str = 'postgres'
    postgres_password: str = 'postgres'
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_db: str = 'postgres'
    database_url: str = (
        f'postgresql+asyncpg://'
        f'{postgres_user}:{postgres_password}'
        f'@{postgres_host}:{postgres_port}/{postgres_db}'
    )
    test_postgres_db: str = 'postgres_test'
    test_database_url: str = (
        f'postgresql+asyncpg://'
        f'{postgres_user}:{postgres_password}'
        f'@{postgres_host}:{postgres_port}/{test_postgres_db}'
    )

    openai_api_key: str = ''
    openai_main_model_name: str = ''
    openai_assessor_model_name: str = ''
    openai_translator_model_name: str = ''
    openai_test_model_name: str = ''
    openai_temperature: float = 0.3
    openai_max_retries: int = 6
    openai_request_timeout: int = 10

    google_api_key: str = ''
    tts_model: str = ''
    google_tts_proxy_url: str = ''
    generate_audio: bool = True

    cloudflare_r2_account_id: str = ''
    cloudflare_r2_access_key_id: str = ''
    cloudflare_r2_secret_access_key: str = ''
    cloudflare_r2_bucket_name: str = 'duoniche'
    cloudflare_r2_public_url_prefix: str = ''

    telegram_upload_bot_tokens_json: str = ''
    telegram_upload_bot_tokens: Dict[str, str] = {}
    telegram_upload_bot_chat_id: str = ''

    redis_url: str = 'redis://localhost:6379'
    redis_test_db: int = 1

    sentry_dsn: str = ''

    worker_shutdown_timeout_seconds: int = 10

    default_bot_message_language: str = 'en'
    exercise_fill_in_the_blank_blanks: str = '___'
    default_language_level: LanguageLevel = LanguageLevel.A2
    default_user_language: str = 'en'
    default_target_language: str = 'Bulgarian'
    max_sessions_length: timedelta = timedelta(hours=3)
    exercises_in_set: int = 5
    sets_in_session: int = 3
    exercises_in_session: int = exercises_in_set * sets_in_session
    delta_between_sessions: timedelta = timedelta(hours=3)
    renewing_set_period: timedelta = timedelta(
        seconds=int(delta_between_sessions.total_seconds() // sets_in_session)
    )

    min_session_unlock_payment: int = 50

    update_user_metrics_interval: int = 60
    session_ttl_since_last_exercise: timedelta = timedelta(minutes=5)

    notification_tasks_queue_name: str = 'notification_tasks_default'
    notification_scheduler_interval_seconds: int = 60 * 5
    long_break_reminders_cooldown_hours: int = 47
    long_break_reminder_time_window_seconds: int = 30 * 60
    long_break_reminder_intervals: Dict[str, timedelta] = {
        '1d': timedelta(days=1),
        '3d': timedelta(days=3),
        '5d': timedelta(days=5),
        '8d': timedelta(days=8),
        '13d': timedelta(days=13),
        '21d': timedelta(days=21),
        '30d': timedelta(days=30),
        '90d': timedelta(days=90),
    }
    long_break_reminder_sequence: List[str] = [
        '1d',
        '3d',
        '5d',
        '8d',
        '13d',
        '21d',
        '30d',
        '90d',
    ]

    async_task_cache_ttl: int = 60 * 2

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @model_validator(mode='after')
    def parse_bot_tokens(self) -> 'Settings':
        try:
            parsed_tokens = json.loads(self.telegram_upload_bot_tokens_json)
            if not isinstance(parsed_tokens, dict):
                raise ValueError('BOT_TOKENS_JSON must be a JSON object')
            self.telegram_upload_bot_tokens = parsed_tokens
        except json.JSONDecodeError as e:
            raise ValueError('Error decoding BOT_TOKENS_JSON') from e
        except ValueError as e:
            raise ValueError(f'Error parsing BOT_TOKENS_JSON: {e}') from e
        return self


settings = Settings()
