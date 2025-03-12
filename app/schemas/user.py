from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    user_id: int = Field(description='User ID')
    telegram_id: int = Field(description='Telegram ID')
    username: str = Field(description='Username')
    name: str = Field(description='Name')
    user_language: str = Field(description='User language')
    target_language: str = Field(description='Target language')
