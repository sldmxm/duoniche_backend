from abc import ABC, abstractmethod

from app.core.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, user: User) -> User:
        raise NotImplementedError
