import logging
from datetime import datetime
from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
    UserStatusInBot,
)
from app.core.enums import LanguageLevel
from app.core.repositories.user_bot_profile_repository import (
    UserBotProfileRepository,
)
from app.db.models import DBUserBotProfile

logger = logging.getLogger(__name__)


class SQLAlchemyUserBotProfileRepository(UserBotProfileRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_all_by_user_id(
        self, user_id: int
    ) -> List[Optional[UserBotProfile]]:
        stmt = select(UserBotProfile).where(
            DBUserBotProfile.user_id == user_id
        )
        result = await self.session.execute(stmt)
        db_profiles = result.scalars().all()
        return [
            UserBotProfile.model_validate(db_profile)
            for db_profile in db_profiles
        ]

    @override
    async def get(self, user_id: int, bot_id: BotID) -> UserBotProfile | None:
        db_profile = await self.session.get(
            DBUserBotProfile, (user_id, bot_id)
        )
        if not db_profile:
            return None
        return UserBotProfile.model_validate(db_profile)

    @override
    async def save(self, profile: UserBotProfile) -> UserBotProfile:
        db_profile = DBUserBotProfile(profile.model_dump())
        self.session.add(db_profile)
        await self.session.commit()
        await self.session.refresh(db_profile)
        return UserBotProfile.model_validate(db_profile)

    @override
    async def update_status(
        self,
        user_id: int,
        bot_id: BotID,
        status: UserStatusInBot,
        reason: Optional[str],
    ) -> UserBotProfile:
        db_profile = await self.session.get(
            DBUserBotProfile, (user_id, bot_id)
        )
        if not db_profile:
            raise ValueError('User profile does not exist')
        db_profile.status = status
        db_profile.reason = reason
        await self.session.commit()
        await self.session.refresh(db_profile)
        return UserBotProfile.model_validate(db_profile)

    @override
    async def update_profile(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        language_level: LanguageLevel,
    ) -> UserBotProfile:
        db_profile = await self.session.get(
            DBUserBotProfile, (user_id, bot_id)
        )
        if not db_profile:
            raise ValueError('User profile does not exist')
        db_profile.user_language = user_language
        db_profile.language_level = language_level
        await self.session.commit()
        await self.session.refresh(db_profile)
        return UserBotProfile.model_validate(db_profile)

    @override
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
        db_profile = await self.session.get(
            DBUserBotProfile, (user_id, bot_id)
        )
        if not db_profile:
            raise ValueError('User profile does not exist')
        db_profile.exercises_get_in_session = exercises_get_in_session
        db_profile.exercises_get_in_set = exercises_get_in_set
        db_profile.errors_count_in_set = errors_count_in_set
        db_profile.last_exercise_at = last_exercise_at
        db_profile.session_started_at = session_started_at
        db_profile.session_frozen_until = session_frozen_until
        await self.session.commit()
        await self.session.refresh(db_profile)
        return UserBotProfile.model_validate(db_profile)
