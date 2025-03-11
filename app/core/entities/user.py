from pydantic import BaseModel


class User(BaseModel):
    user_id: int
    telegram_id: int
    username: str
    name: str = ''
    language_level: str = 'beginner'
    is_active: bool = True
    user_language: str | None = 'Russian'
    target_language: str | None = 'Bulgarian'
