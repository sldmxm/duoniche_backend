import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.config import settings
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

_ALLOWED_SESSION_UPDATE_FIELDS = {
    'exercises_get_in_session',
    'exercises_get_in_set',
    'errors_count_in_set',
    'last_exercise_at',
    'session_started_at',
    'session_frozen_until',
    'last_long_break_reminder_type_sent',
    'last_long_break_reminder_sent_at',
    'current_streak_days',
    'wants_session_reminders',
}

_ALLOWED_PROFILE_UPDATE_FIELDS = {
    'user_language',
    'language_level',
    'wants_session_reminders',
}


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
        language_level: LanguageLevel = settings.default_language_level,
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
            wants_session_reminders=None,
            last_long_break_reminder_type_sent=None,
            last_long_break_reminder_sent_at=None,
            rating=None,
            rating_last_calculated_at=None,
            settings=None,
            last_report_generated_at=None,
            current_streak_days=0,
        )
        try:
            created_profile = await self._profile_repo.create(new_profile)
            is_created = True
            return created_profile, is_created
        except Exception as e:
            logger.error(
                f'Error creating profile '
                f'for user {user_id}, bot {bot_id}: {e}'
            )
            raise

    async def _apply_and_save_changes(
        self,
        profile: UserBotProfile,
        fields_to_update: Dict[str, Any],
        allowed_fields: Set[str],
    ) -> UserBotProfile:
        actual_changes: Dict[str, Any] = {}
        for key, value in fields_to_update.items():
            if key in allowed_fields:
                if hasattr(profile, key) and getattr(profile, key) != value:
                    actual_changes[key] = value
            else:
                logger.error(
                    f"Unknown or non-allowed field '{key}' provided to update"
                    f'for user {profile.user_id}, bot {profile.bot_id}.'
                )
        if not actual_changes:
            return profile
        for key, value in actual_changes.items():
            setattr(profile, key, value)

        try:
            updated_profile = await self._profile_repo.update(profile)
            return updated_profile
        except Exception as e:
            logger.error(
                f'Error saving profile updates '
                f'for {profile.user_id}/{profile.bot_id}: {e}'
            )
            raise

    async def update_session(
        self,
        user_id: int,
        bot_id: BotID,
        **fields_to_update: Union[int, datetime, None],
    ) -> UserBotProfile:
        profile = await self.get(user_id=user_id, bot_id=bot_id)
        if not profile:
            raise ValueError(
                f'Profile not found for user {user_id}, '
                f'bot {bot_id} to update session.'
            )

        if not fields_to_update:
            return profile

        return await self._apply_and_save_changes(
            profile, fields_to_update, _ALLOWED_SESSION_UPDATE_FIELDS
        )

    async def update_profile(
        self,
        user_id: int,
        bot_id: BotID,
        **fields_to_update: Union[str, LanguageLevel, bool, None],
    ) -> UserBotProfile:
        profile = await self.get(user_id=user_id, bot_id=bot_id)
        if not profile:
            raise ValueError(
                f'Profile not found for user {user_id}, '
                f'bot {bot_id} to update profile.'
            )

        if not fields_to_update:
            return profile

        return await self._apply_and_save_changes(
            profile, fields_to_update, _ALLOWED_PROFILE_UPDATE_FIELDS
        )

    async def mark_user_active(
        self, user_id: int, bot_id: BotID
    ) -> UserBotProfile:
        profile = await self.get(user_id=user_id, bot_id=bot_id)
        if not profile:
            raise ValueError(
                f'Profile not found for user {user_id}, '
                f'bot {bot_id} to update profile.'
            )

        if (
            profile.status != UserStatusInBot.ACTIVE
            or profile.reason is not None
        ):
            profile.status = UserStatusInBot.ACTIVE
            profile.reason = None

            try:
                updated_profile = await self._profile_repo.update(profile)
                return updated_profile
            except Exception as e:
                logger.error(f'Error updating profile: {e}')
                raise
        else:
            return profile

    async def mark_user_blocked(
        self,
        user_id: int,
        bot_id: BotID,
        reason: Optional[str],
    ) -> UserBotProfile:
        profile = await self.get(user_id=user_id, bot_id=bot_id)
        if not profile:
            raise ValueError(
                f'Profile not found for user {user_id}, '
                f'bot {bot_id} to update profile.'
            )

        if (
            profile.status != UserStatusInBot.BLOCKED
            or profile.reason != reason
        ):
            profile.status = UserStatusInBot.BLOCKED
            profile.reason = reason
            try:
                updated_profile = await self._profile_repo.update(profile)
                return updated_profile
            except Exception as e:
                logger.error(f'Error updating profile: {e}')
                raise
        else:
            return profile

    async def reset_and_start_new_session(
        self, user_id: int, bot_id: BotID
    ) -> UserBotProfile:
        """
        Resets all session-related counters and starts
        a new session for the user.
        Sets session_frozen_until to None.
        """
        now = datetime.now(timezone.utc)
        updated_profile = await self.update_session(
            user_id=user_id,
            bot_id=bot_id,
            exercises_get_in_session=0,
            exercises_get_in_set=0,
            errors_count_in_set=0,
            session_started_at=now,
            session_frozen_until=None,
            wants_session_reminders=None,
            last_long_break_reminder_type_sent=None,
            last_long_break_reminder_sent_at=None,
        )
        if not updated_profile:
            raise ValueError(
                f'Failed to update profile for user '
                f'{user_id}, bot {bot_id} to unlock session.'
            )
        logger.info(
            f'Session unlocked for user {user_id}, ' f'bot {bot_id.value}.'
        )
        return updated_profile
