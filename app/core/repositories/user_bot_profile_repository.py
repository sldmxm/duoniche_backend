from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
)


class UserBotProfileRepository(ABC):
    @abstractmethod
    async def get_all_by_user_id(
        self, user_id: int
    ) -> List[Optional[UserBotProfile]]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, user_id: int, bot_id: BotID) -> UserBotProfile | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, profile: UserBotProfile) -> UserBotProfile:
        raise NotImplementedError

    @abstractmethod
    async def create(self, profile: UserBotProfile) -> UserBotProfile:
        raise NotImplementedError
