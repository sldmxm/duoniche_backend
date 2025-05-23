from typing import Optional

from pydantic import BaseModel, Field

from app.config import settings


class UserCreate(BaseModel):
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
    telegram_data: Optional[dict] = Field(
        description='Telegram data', default=None
    )


class UserUpdate(BaseModel):
    user_id: int = Field(description='User ID')
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
    telegram_data: Optional[dict] = Field(
        description='Telegram data', default=None
    )


class UserResponse(BaseModel):
    user_id: int = Field(description='User ID')
    telegram_id: str = Field(description='Telegram ID')
    username: Optional[str] = Field(description='Username')
    name: Optional[str] = Field(description='Name')
    user_language: str = Field(
        description='User language',
    )
    telegram_data: Optional[dict] = Field(description='Telegram data')
    language_level: Optional[str] = Field(
        description='User language level',
        default=settings.default_language_level.value,
    )
    cohort: Optional[str] = Field(description='Cohort')
    plan: Optional[str] = Field(description='Plan')
