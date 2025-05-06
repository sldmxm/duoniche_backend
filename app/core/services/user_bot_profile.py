import logging
from datetime import datetime
from typing import List, Optional

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
    UserStatusInBot,
)
from app.core.enums import LanguageLevel
from app.core.repositories.user_bot_profile_repository import (
    UserBotProfileRepository,
)

logger = logging.getLogger(__name__)


class UserBotProfileService:
    def __init__(self, profile_repo: UserBotProfileRepository):
        self._profile_repo = profile_repo

    async def get_all_by_user_id(
        self, user_id: int
    ) -> List[Optional[UserBotProfile]]:
        profiles = await self._profile_repo.get_all_by_user_id(user_id)
        return profiles

    async def get(self, user_id: int, bot_id: BotID) -> UserBotProfile | None:
        profile = await self._profile_repo.get(user_id, bot_id)
        return profile

    async def save(self, profile: UserBotProfile) -> UserBotProfile:
        profile = await self._profile_repo.save(profile)
        return profile

    async def get_or_create(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL,
    ) -> UserBotProfile | None:
        profile = await self._profile_repo.get(user_id, bot_id)
        if profile:
            return profile
        new_profile = UserBotProfile(
            user_id=user_id,
            bot_id=bot_id,
            status=UserStatusInBot.ACTIVE,
            reason=None,
            user_language=user_language,
            language_level=language_level,
            exercises_get_in_session=0,
            exercises_get_in_set=0,
            errors_count_in_set=0,
            last_exercise_at=None,
            session_started_at=None,
            session_frozen_until=None,
        )
        profile = await self._profile_repo.save(new_profile)
        return profile

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
        profile = await self._profile_repo.update_session(
            user_id=user_id,
            bot_id=bot_id,
            exercises_get_in_session=exercises_get_in_session,
            exercises_get_in_set=exercises_get_in_set,
            errors_count_in_set=errors_count_in_set,
            last_exercise_at=last_exercise_at,
            session_started_at=session_started_at,
            session_frozen_until=session_frozen_until,
        )
        return profile

    async def update_profile(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel,
    ) -> UserBotProfile:
        profile = await self._profile_repo.update_profile(
            user_id=user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=language_level,
        )
        return profile

    async def mark_user_blocked(
        self, user_id: int, bot_id: BotID, reason: Optional[str] = None
    ) -> UserBotProfile:
        profile = await self._profile_repo.update_status(
            user_id=user_id,
            bot_id=bot_id,
            status=UserStatusInBot.BLOCKED,
            reason=reason,
        )
        return profile

    async def mark_user_active(
        self, user_id: int, bot_id: BotID
    ) -> UserBotProfile:
        profile = await self._profile_repo.update_status(
            user_id=user_id,
            bot_id=bot_id,
            status=UserStatusInBot.ACTIVE,
            reason=None,
        )
        return profile
