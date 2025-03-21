from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    telegram_id: int = Field(description='Telegram ID')
    username: str = Field(description='Username')
    name: str = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')


class UserResponse(BaseModel):
    user_id: int = Field(description='User ID')
    # TODO: Понять насколько надо передавать остальное,
    #  в телеге, например, оно и так уже есть
    telegram_id: int = Field(description='Telegram ID')
    username: str = Field(description='Username')
    name: str = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
