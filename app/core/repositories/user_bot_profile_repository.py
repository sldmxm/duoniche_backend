from abc import abstractmethod
from datetime import datetime
from typing import List, Optional

from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
    UserStatusInBot,
)
from app.core.enums import LanguageLevel
from app.core.repositories.base import AsyncRepository


class UserBotProfileRepository(AsyncRepository[UserBotProfile]):
    @abstractmethod
    async def get_all_by_user_id(
        self, user_id: int
    ) -> List[Optional[UserBotProfile]]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, user_id: int, bot_id: BotID) -> UserBotProfile | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, profile: UserBotProfile) -> UserBotProfile:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        user_id: int,
        bot_id: BotID,
        status: UserStatusInBot,
        reason: Optional[str],
    ) -> UserBotProfile:
        raise NotImplementedError

    @abstractmethod
    async def update_profile(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel,
    ) -> UserBotProfile:
        raise NotImplementedError

    @abstractmethod
    async def update_session(
        self,
        user_id: int,
        bot_id: BotID,
        exercises_get_in_session: int,
        exercises_get_in_set: int,
        errors_count_in_set: int,
        last_exercise_at: Optional[datetime],
        session_started_at: Optional[datetime],
        session_frozen_until: Optional[datetime],
    ) -> UserBotProfile:
        raise NotImplementedError
