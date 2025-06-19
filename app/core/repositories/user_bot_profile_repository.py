from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.entities.user import User
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

    @abstractmethod
    async def calc_and_store_ratings_for_profiles(
        self,
    ) -> Dict[Tuple[int, BotID], float]:
        """
        Calculates ratings for the given user/bot profiles based on
        their attempt history and stores them in the DB.
        Returns a map of (user_id, bot_id) to new rating.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_active_profiles_for_reporting(
        self, since: datetime
    ) -> List[Tuple[UserBotProfile, User]]:
        raise NotImplementedError
