from pydantic_settings import BaseSettings


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
    test_postgres_db: str = 'learnbg_test'
    test_database_url: str = (
        f'postgresql+asyncpg://'
        f'{postgres_user}:{postgres_password}'
        f'@{postgres_host}:{postgres_port}/{test_postgres_db}'
    )

    openai_api_key: str = ''
    openai_model_name: str = ''
    openai_test_model_name: str = ''
    openai_temperature: float = 0.3
    openai_max_retries: int = 6
    openai_request_timeout: int = 10

    google_api_key: str = ''

    redis_url: str = 'redis://localhost:6379'
    redis_test_db: int = 1

    # нет смысла дольше, уже будет в БД и новые не будут начаты
    async_task_cache_ttl: int = 60 * 2

    sentry_dsn: str = ''

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
