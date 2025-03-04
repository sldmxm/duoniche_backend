from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    telegram_id: int
    name: str | None = None
    username: str | None = None
    language_level: str = 'beginner'
    is_active: bool = True
