from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore
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
    openai_temperature: float = 0.3
    openai_max_retries: int = 6
    openai_request_timeout: int = 10

    debug: str = 'False'

    telegram_token: str = ''
    use_webhook: str = ''
    webhook_secret: str = ''
    base_webhook_url: str = ''
    webhook_path: str = ''
    webapp_host: str = 'localhost'
    webapp_port: int = 8080

    redis_url: str = 'redis://localhost:6379'

    api_url: str = 'http://localhost:8000'

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )


settings = Settings()
