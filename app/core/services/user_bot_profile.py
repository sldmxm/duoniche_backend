import logging
from datetime import datetime
from typing import List, Optional, Tuple

from app.core.consts import DEFAULT_LANGUAGE_LEVEL, DEFAULT_USER_LANGUAGE
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
        profile = await self._profile_repo.update(profile)
        return profile

    async def get_or_create(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL,
    ) -> Tuple[UserBotProfile, bool]:
        profile = await self._profile_repo.get(user_id, bot_id)
        if profile:
            is_created = False
            return profile, is_created

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
        try:
            created_profile = await self._profile_repo.create(new_profile)
            is_created = True
            return created_profile, is_created
        except Exception as e:
            logger.error(f'Error creating profile: {e}')
            raise

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
        profile, _ = await self.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=DEFAULT_USER_LANGUAGE,
            language_level=DEFAULT_LANGUAGE_LEVEL,
        )

        profile.exercises_get_in_session = exercises_get_in_session
        profile.exercises_get_in_set = exercises_get_in_set
        profile.errors_count_in_set = errors_count_in_set
        profile.last_exercise_at = last_exercise_at
        profile.session_started_at = session_started_at
        profile.session_frozen_until = session_frozen_until

        try:
            updated_profile = await self._profile_repo.update(profile)
            return updated_profile
        except Exception as e:
            logger.error(f'Error updating profile: {e}')
            raise

    async def update_profile(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel,
    ) -> UserBotProfile:
        profile, is_created = await self.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=language_level,
        )
        if is_created:
            return profile

        profile.user_language = user_language
        profile.language_level = language_level
        try:
            updated_profile = await self._profile_repo.update(profile)
            return updated_profile
        except Exception as e:
            logger.error(f'Error updating profile: {e}')
            raise

    async def mark_user_active(
        self, user_id: int, bot_id: BotID
    ) -> UserBotProfile:
        profile, is_created = await self.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=DEFAULT_USER_LANGUAGE,
            language_level=DEFAULT_LANGUAGE_LEVEL,
        )

        if is_created:
            return profile

        profile.status = UserStatusInBot.ACTIVE
        profile.reason = None

        try:
            updated_profile = await self._profile_repo.update(profile)
            return updated_profile
        except Exception as e:
            logger.error(f'Error updating profile: {e}')
            raise

    async def mark_user_blocked(
        self,
        user_id: int,
        bot_id: BotID,
        reason: Optional[str],
    ) -> UserBotProfile:
        profile, _ = await self.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=DEFAULT_USER_LANGUAGE,
            language_level=DEFAULT_LANGUAGE_LEVEL,
        )

        profile.status = UserStatusInBot.BLOCKED
        profile.reason = reason

        try:
            updated_profile = await self._profile_repo.update(profile)
            return updated_profile
        except Exception as e:
            logger.error(f'Error updating profile: {e}')
            raise
