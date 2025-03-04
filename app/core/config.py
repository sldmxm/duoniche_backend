from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore
    database_url: str
    test_database_url: str = ''
    postgres_user: str
    postgres_password: str
    postgres_host: str = 'localhost'
    postgres_port: int = 5432
    postgres_db: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
    )


settings = Settings()
