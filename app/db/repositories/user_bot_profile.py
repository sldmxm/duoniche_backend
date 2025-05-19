import logging
from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, override

from sqlalchemy import Time, cast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
    UserStatusInBot,
)
from app.core.repositories.user_bot_profile_repository import (
    UserBotProfileRepository,
)
from app.db.models import DBUserBotProfile

logger = logging.getLogger(__name__)


class SQLAlchemyUserBotProfileRepository(UserBotProfileRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def create(self, profile: UserBotProfile) -> UserBotProfile:
        new_db_profile = DBUserBotProfile(**profile.model_dump())
        self.session.add(new_db_profile)
        try:
            await self.session.commit()
            await self.session.refresh(new_db_profile)
        except Exception as e:
            await self.session.rollback()
            logger.error(f'Error creating UserBotProfile: {e}')
            raise
        return UserBotProfile.model_validate(new_db_profile)

    @override
    async def get_all_by_user_id(
        self, user_id: int
    ) -> List[Optional[UserBotProfile]]:
        stmt = select(DBUserBotProfile).where(
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
    async def update(self, profile: UserBotProfile) -> UserBotProfile:
        existing_db_profile = await self.session.get(
            DBUserBotProfile, (profile.user_id, profile.bot_id)
        )

        if not existing_db_profile:
            raise ValueError(
                f'Profile not found for user {profile.user_id} '
                f'and bot {profile.bot_id}'
            )

        for key, value in profile.model_dump(exclude_unset=True).items():
            setattr(existing_db_profile, key, value)
        db_profile_to_commit = existing_db_profile

        try:
            await self.session.commit()
            await self.session.refresh(db_profile_to_commit)
        except Exception as e:
            await self.session.rollback()
            logger.error(f'Error saving UserBotProfile: {e}')
            raise

        return UserBotProfile.model_validate(db_profile_to_commit)

    async def get_by_recent_exercise_with_user_data(
        self, period_seconds: int
    ) -> List[DBUserBotProfile]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(DBUserBotProfile)
            .where(
                DBUserBotProfile.last_exercise_at.isnot(None),
                DBUserBotProfile.last_exercise_at
                >= now - timedelta(seconds=period_seconds),
            )
            .options(joinedload(DBUserBotProfile.user))
        )
        result = await self.session.execute(stmt)
        db_user_bot_profiles = result.scalars().unique().all()
        return list(db_user_bot_profiles)

    async def get_unfrozen_for_reminder(
        self, period_seconds: int
    ) -> List[DBUserBotProfile]:
        now = datetime.now(timezone.utc)
        window_start_time = now - timedelta(seconds=period_seconds)

        stmt = (
            select(DBUserBotProfile)
            .where(
                DBUserBotProfile.session_frozen_until.isnot(None),
                DBUserBotProfile.wants_session_reminders.isnot(False),
                DBUserBotProfile.status == UserStatusInBot.ACTIVE,
                DBUserBotProfile.session_frozen_until > window_start_time,
                DBUserBotProfile.session_frozen_until <= now,
            )
            .options(joinedload(DBUserBotProfile.user))
        )
        result = await self.session.execute(stmt)
        db_user_bot_profiles = result.scalars().unique().all()
        return list(db_user_bot_profiles)

    async def get_with_long_break_for_reminder(
        self,
        min_break_duration_seconds: int,
        window_start_time: time,
        window_end_time: time,
    ) -> List[DBUserBotProfile]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(DBUserBotProfile)
            .where(
                DBUserBotProfile.status == UserStatusInBot.ACTIVE,
                DBUserBotProfile.last_exercise_at.isnot(None),
                DBUserBotProfile.last_exercise_at
                <= now - timedelta(seconds=min_break_duration_seconds),
                cast(DBUserBotProfile.last_exercise_at, Time)
                >= window_start_time,
                cast(DBUserBotProfile.last_exercise_at, Time)
                <= window_end_time,
            )
            .options(joinedload(DBUserBotProfile.user))
        )
        result = await self.session.execute(stmt)
        db_user_bot_profiles = result.scalars().unique().all()
        return list(db_user_bot_profiles)
