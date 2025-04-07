from abc import abstractmethod
from typing import List, Optional

from app.core.entities.user import User
from app.core.repositories.base import AsyncRepository


class UserRepository(AsyncRepository[User]):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> List[User]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_users_with_exercise_lately(
        self, period_seconds: int
    ) -> List[User]:
        raise NotImplementedError
