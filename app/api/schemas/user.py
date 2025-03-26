from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')


class UserUpdate(BaseModel):
    user_id: int = Field(description='User ID')
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
    language_level: Optional[str] = Field(description='User language level')


class UserResponse(BaseModel):
    user_id: int = Field(description='User ID')
    # TODO: Понять насколько надо передавать остальное,
    #  в телеге, например, оно и так уже есть
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
    language_level: Optional[str] = Field(description='User language level')
