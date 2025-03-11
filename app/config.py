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
    test_database_url: str = ''

    openai_api_key: str = ''
    openai_model_name: str = ''
    openai_temperature: float = 0.7
    openai_max_retries: int = 6
    openai_request_timeout: int = 10

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )


settings = Settings()
