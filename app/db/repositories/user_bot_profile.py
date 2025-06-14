import logging
from datetime import datetime, time, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, override

from sqlalchemy import Time, cast, select, text, update
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
            await self.session.flush()
            await self.session.refresh(new_db_profile)
        except Exception as e:
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

        profile_data_to_update = profile.model_dump(exclude_unset=True)
        for key, value in profile_data_to_update.items():
            if isinstance(getattr(profile, key, None), Enum) and isinstance(
                value, str
            ):
                enum_field = getattr(profile, key)
                try:
                    setattr(existing_db_profile, key, type(enum_field)(value))
                except ValueError:
                    setattr(existing_db_profile, key, value)
            else:
                setattr(existing_db_profile, key, value)

        try:
            await self.session.flush()
            await self.session.refresh(existing_db_profile)
        except Exception as e:
            logger.error(f'Error saving UserBotProfile: {e}', exc_info=True)
            raise

        return UserBotProfile.model_validate(existing_db_profile)

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
                DBUserBotProfile.wants_session_reminders,
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

    async def get_all(self) -> List[UserBotProfile]:
        stmt = select(DBUserBotProfile)
        result = await self.session.execute(stmt)
        db_profiles = result.scalars().all()
        return [UserBotProfile.model_validate(p) for p in db_profiles]

    @override
    async def calc_and_store_ratings_for_profiles(
        self,
    ) -> Dict[Tuple[int, BotID], float]:
        """
        Calculates ratings for all users per bot_id based on their
        attempt history and updates the DBUserBotProfile.
        Returns a map of (user_id, bot_id) to new rating.
        """
        sql_query = """
            WITH user_lang_stats AS (
                SELECT
                    ea.user_id,
                    ex.exercise_language,
                    COUNT(DISTINCT DATE(ea.created_at)) AS active_days,
                    COUNT(ea.attempt_id) AS total_attempts,
                    AVG(CASE WHEN ea.is_correct IS TRUE THEN 1 ELSE 0 END)
                        AS correct_ratio
                FROM exercise_attempts ea
                JOIN exercises ex ON ea.exercise_id = ex.exercise_id
                GROUP BY ea.user_id, ex.exercise_language
            ),
            user_lang_norms_intermediate AS (
                SELECT
                    user_id,
                    exercise_language,
                    active_days,
                    LOG(1 + total_attempts) AS log_total_attempts,
                    correct_ratio,
                    MIN(active_days) OVER () as min_active_days_global,
                    MAX(active_days) OVER () as max_active_days_global,
                    MIN(LOG(1 + total_attempts)) OVER ()
                        as min_log_attempts_global,
                    MAX(LOG(1 + total_attempts)) OVER ()
                        as max_log_attempts_global
                FROM user_lang_stats
            ),
            user_lang_norms AS (
                SELECT
                    user_id,
                    exercise_language,
                    active_days,
                    log_total_attempts,
                    correct_ratio,
                    (active_days - min_active_days_global)::float /
                        NULLIF(
                            (max_active_days_global - min_active_days_global),
                            0) AS norm_active_days,
                    (log_total_attempts - min_log_attempts_global)::float /
                        NULLIF(
                            (max_log_attempts_global
                                - min_log_attempts_global),
                            0) AS norm_log_attempts
                FROM user_lang_norms_intermediate
                WHERE (max_active_days_global - min_active_days_global) > 0
                  AND (max_log_attempts_global - min_log_attempts_global) > 0
            )
            SELECT
                s.user_id,
                s.exercise_language, -- Это будет наш BotID.value
                COALESCE(s.correct_ratio, 0) as correct_ratio,
                COALESCE(n.norm_active_days, 0) as norm_active_days,
                COALESCE(n.norm_log_attempts, 0) as norm_log_attempts,
                ROUND(
                    (0.4 * COALESCE(n.norm_active_days, 0) +
                     0.3 * COALESCE(n.norm_log_attempts, 0) +
                     0.3 * COALESCE(s.correct_ratio, 0)
                    )::numeric, 4
                ) AS user_rating
            FROM user_lang_stats s
            LEFT JOIN user_lang_norms n ON s.user_id = n.user_id
                AND s.exercise_language = n.exercise_language;
            """
        result = await self.session.execute(text(sql_query))
        calculated_ratings: Dict[Tuple[int, str], float] = {}
        for row in result.fetchall():
            user_id, lang_str, _, _, _, rating = row
            if rating is not None:
                calculated_ratings[(user_id, lang_str)] = float(rating)

        updated_ratings_map: Dict[Tuple[int, BotID], float] = {}
        now = datetime.now(timezone.utc)

        for (user_id, lang_str), rating_value in calculated_ratings.items():
            try:
                bot_id_enum = BotID(lang_str)
                stmt = (
                    update(DBUserBotProfile)
                    .where(
                        DBUserBotProfile.user_id == user_id,
                        DBUserBotProfile.bot_id == bot_id_enum,
                    )
                    .values(rating=rating_value, rating_last_calculated_at=now)
                    .execution_options(synchronize_session=False)
                )
                await self.session.execute(stmt)
                updated_ratings_map[(user_id, bot_id_enum)] = rating_value
            except ValueError:
                logger.warning(
                    f"Unknown language string '{lang_str}' encountered "
                    f'in rating calculation, cannot map to BotID.'
                )
            except Exception as e:
                logger.error(
                    f'Error updating rating for '
                    f'user {user_id}, bot {lang_str}: {e}',
                    exc_info=True,
                )

        logger.info(
            f'Calculated and attempted to store ratings '
            f'for {len(updated_ratings_map)} user/bot profiles.'
        )
        return updated_ratings_map
