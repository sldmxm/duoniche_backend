from pydantic import BaseModel


class User(BaseModel):
    user_id: int
    telegram_id: int
    username: str | None = None
    name: str | None = None
    language_level: str = 'beginner'
    is_active: bool = True
    user_language: str = 'Russian'
    target_language: str = 'Bulgarian'
