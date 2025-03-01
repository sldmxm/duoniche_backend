from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    telegram_id: int
    username: str | None = None
    language_level: str = 'beginner'
