from abc import abstractmethod

from app.core.entities.user import User
from app.core.repositories.base import AsyncRepository


class UserRepository(AsyncRepository[User]):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> User:
        raise NotImplementedError
