import logging
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis as AsyncRedis

from app.core.entities.user_settings import UserSettings
from app.core.enums import UserStatus
from app.core.services.language_config import LanguageConfigService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.user_settings_templates import (
    FREE_PLAN_SETTINGS,
    PREMIUM_PLAN_SETTINGS,
    TRIAL_PLAN_SETTINGS,
)

logger = logging.getLogger(__name__)


class UserSettingsService:
    def __init__(
        self,
        user_service: UserService,
        user_bot_profile_service: UserBotProfileService,
        redis_client: AsyncRedis,
        language_config_service: LanguageConfigService,
    ):
        self._user_service = user_service
        self._profile_service = user_bot_profile_service
        self._redis = redis_client
        self._language_config_service = language_config_service

    def _get_cache_key(self, user_id: int, bot_id: str) -> str:
        return f'user_settings:{user_id}:{bot_id}'

    async def invalidate_user_settings_cache(self, user_id: int, bot_id: str):
        key = self._get_cache_key(user_id, bot_id)
        await self._redis.delete(key)
        logger.info(f'Invalidated settings cache for user {user_id}/{bot_id}')

    async def get_effective_settings(
        self, user_id: int, bot_id: str
    ) -> UserSettings:
        cache_key = self._get_cache_key(user_id, bot_id)
        cached_settings = await self._redis.get(cache_key)
        if cached_settings:
            try:
                return UserSettings.model_validate_json(cached_settings)
            except Exception as e:
                logger.warning(
                    f'Failed to deserialize cached settings for {cache_key}: '
                    f'{e}. Re-fetching.'
                )

        user = await self._user_service.get_by_id(user_id)
        if not user:
            raise ValueError(f'User not found: {user_id}')

        profile = await self._profile_service.get(user_id, bot_id)
        if not profile:
            raise ValueError(
                f'UserBotProfile not found for {user_id}/{bot_id}'
            )

        if (
            user.status != UserStatus.FREE
            and user.status_expires_at
            and user.status_expires_at < datetime.now(timezone.utc)
        ):
            logger.info(
                f'User {user_id} status {user.status.value} expired. '
                f'Downgrading to free.'
            )
            user.status = UserStatus.FREE
            user.status_expires_at = None
            user.status_source = 'expired'
            user = await self._user_service.update(
                user_id=user_id,
                status=user.status,
                status_expires_at=user.status_expires_at,
                status_source=user.status_source,
            )
            await self.invalidate_user_settings_cache(user_id, bot_id)

        plan_templates = {
            UserStatus.FREE: FREE_PLAN_SETTINGS,
            UserStatus.TRIAL: TRIAL_PLAN_SETTINGS,
            UserStatus.PREMIUM: PREMIUM_PLAN_SETTINGS,
        }

        plan_to_use = (
            user.status if user.status in plan_templates else UserStatus.FREE
        )
        effective_settings = plan_templates[plan_to_use].model_copy(deep=True)

        lang_service = self._language_config_service
        distribution = lang_service.get_exercise_types_distribution(bot_id)
        if distribution:
            effective_settings.exercise_type_distribution = {
                k: v
                for k, v in distribution.items()
                if k in effective_settings.available_exercise_types
            }

        logger.info(
            f'Discovered effective settings from lang and plan:'
            f' {effective_settings}'
        )

        if user.custom_settings:
            effective_settings = effective_settings.model_copy(
                update=user.custom_settings.model_dump(exclude_unset=True),
            )

        logger.info(
            f'Discovered effective settings from user.custom_settings:'
            f' {effective_settings}'
        )

        if profile.settings:
            effective_settings = effective_settings.model_copy(
                update=profile.settings.model_dump(exclude_unset=True)
            )

        logger.info(
            f'Discovered effective settings from profile.settings:'
            f' {effective_settings}'
        )

        await self._redis.set(
            cache_key,
            effective_settings.model_dump_json(),
            ex=timedelta(hours=1),
        )

        return effective_settings
