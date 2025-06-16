import logging
from typing import List, Optional, Union, override

from sqlalchemy import and_, exists, func, literal, not_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise import Exercise
from app.core.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.generation.config import ExerciseTopic
from app.core.repositories.exercise import ExerciseRepository
from app.core.value_objects.exercise import ExerciseData
from app.db.models import Exercise as ExerciseModel
from app.db.models import ExerciseAttempt as ExerciseAttemptModel

logger = logging.getLogger(__name__)


class SQLAlchemyExerciseRepository(ExerciseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _to_entity(self, db_exercise: ExerciseModel) -> Exercise:
        """Converts an ExerciseModel to an Exercise
        entity using Pydantic validation."""
        exercise_dict = {
            column.name: getattr(db_exercise, column.name)
            for column in db_exercise.__table__.columns
        }
        return Exercise.model_validate(exercise_dict)

    async def _to_db_model(self, exercise: Exercise) -> ExerciseModel:
        """Converts an Exercise entity to an ExerciseModel."""
        return ExerciseModel(
            exercise_id=exercise.exercise_id,
            exercise_type=exercise.exercise_type.value,
            exercise_language=exercise.exercise_language,
            language_level=exercise.language_level.value,
            topic=exercise.topic.value,
            exercise_text=exercise.exercise_text,
            status=exercise.status,
            persona=exercise.persona,
            comments=exercise.comments,
            grammar_tags=exercise.grammar_tags,
            data=exercise.data.model_dump(),
        )

    @override
    async def get_by_id(self, exercise_id: int) -> Optional[Exercise]:
        db_exercise = await self.session.get(ExerciseModel, exercise_id)
        if not db_exercise:
            return None
        return await self._to_entity(db_exercise)

    @override
    async def get_new_exercise(
        self,
        user_id: int,
        target_language: str,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> Optional[Exercise]:
        answered_exercise_exists_subquery = select(literal(1)).where(
            and_(
                ExerciseAttemptModel.user_id == user_id,
                ExerciseAttemptModel.exercise_id == ExerciseModel.exercise_id,
            )
        )

        stmt = (
            select(ExerciseModel)
            .where(
                and_(
                    ExerciseModel.language_level == language_level.value,
                    ExerciseModel.exercise_type == exercise_type.value,
                    ExerciseModel.exercise_language == target_language,
                    ExerciseModel.topic == topic.value,
                    ExerciseModel.status == ExerciseStatus.PUBLISHED,
                    not_(exists(answered_exercise_exists_subquery)),
                )
            )
            .order_by(func.random())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        db_exercise = result.scalar_one_or_none()
        if db_exercise is None:
            return None

        return await self._to_entity(db_exercise)

    @override
    async def get_any_new_exercise(
        self,
        user_id: int,
        target_language: str,
        exercise_type: Optional[ExerciseType],
    ) -> Optional[Exercise]:
        answered_exercise_exists_subquery = select(literal(1)).where(
            and_(
                ExerciseAttemptModel.user_id == user_id,
                ExerciseAttemptModel.exercise_id == ExerciseModel.exercise_id,
            )
        )

        conditions = [
            ExerciseModel.exercise_language == target_language,
            ExerciseModel.status == ExerciseStatus.PUBLISHED,
            not_(exists(answered_exercise_exists_subquery)),
        ]
        if exercise_type is not None:
            conditions.append(
                ExerciseModel.exercise_type == exercise_type.value
            )

        stmt = (
            select(ExerciseModel)
            .where(and_(*conditions))
            .order_by(func.random())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        db_exercise = result.scalar_one_or_none()
        if db_exercise is None:
            logger.info(f'No any new exercises found for user {user_id}')
            return None
        return await self._to_entity(db_exercise)

    @override
    async def get_any_for_repetition(
        self,
        user_id: int,
        target_language: str,
    ) -> Optional[Exercise]:
        answered_exercise_exists_subquery = select(literal(1)).where(
            and_(
                ExerciseAttemptModel.user_id == user_id,
                ExerciseAttemptModel.exercise_id == ExerciseModel.exercise_id,
            )
        )

        stmt = (
            select(ExerciseModel)
            .where(
                and_(
                    ExerciseModel.exercise_language == target_language,
                    ExerciseModel.status == ExerciseStatus.PUBLISHED,
                    exists(answered_exercise_exists_subquery),
                )
            )
            .order_by(func.random())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        db_exercise = result.scalar_one_or_none()
        if db_exercise is None:
            return None
        return await self._to_entity(db_exercise)

    @override
    async def get_mistake_repetition(
        self,
        user_id: int,
        target_language: str,
    ) -> Optional[Exercise]:
        incorrect_answered_subquery = select(literal(1)).where(
            and_(
                ExerciseAttemptModel.user_id == user_id,
                ExerciseAttemptModel.exercise_id == ExerciseModel.exercise_id,
                not_(ExerciseAttemptModel.is_correct),
            )
        )

        stmt = (
            select(ExerciseModel)
            .where(
                and_(
                    ExerciseModel.exercise_language == target_language,
                    ExerciseModel.status == ExerciseStatus.PUBLISHED,
                    exists(incorrect_answered_subquery),
                )
            )
            .order_by(func.random())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        db_exercise = result.scalar_one_or_none()
        if db_exercise is None:
            return None
        return await self._to_entity(db_exercise)

    @override
    async def create(self, exercise: Exercise) -> Exercise:
        db_exercise = await self._to_db_model(exercise)
        self.session.add(db_exercise)
        await self.session.flush()
        await self.session.refresh(db_exercise)
        return await self._to_entity(db_exercise)

    async def count_untouched_exercises(
        self,
    ) -> dict[str, dict[str, int]]:
        attempts_exist = select(literal(1)).where(
            ExerciseAttemptModel.exercise_id == ExerciseModel.exercise_id
        )

        stmt = (
            select(
                ExerciseModel.exercise_language,
                ExerciseModel.exercise_type,
                func.count().label('count'),
            )
            .where(
                and_(
                    ExerciseModel.status == ExerciseStatus.PUBLISHED,
                    not_(exists(attempts_exist)),
                )
            )
            .group_by(
                ExerciseModel.exercise_language, ExerciseModel.exercise_type
            )
        )

        result = await self.session.execute(stmt)

        counts: dict[str, dict[str, int]] = {}
        for lang, ex_type_str, count_val in result:
            counts.setdefault(lang, {})[ex_type_str] = count_val

        return counts

    async def get_and_lock_exercise_with_audio_error(
        self,
        exercise_type: ExerciseType,
        target_language: str,
    ) -> Optional[Exercise]:
        """
        Finds an exercise with AUDIO_GENERATION_ERROR status
        for the given type, atomically updates its status to
        PROCESSING_ERROR_RETRY, and returns it.
        """
        stmt = (
            select(ExerciseModel)
            .where(
                ExerciseModel.exercise_type == exercise_type.value,
                ExerciseModel.exercise_language == target_language,
                ExerciseModel.status == ExerciseStatus.AUDIO_GENERATION_ERROR,
            )
            .order_by(ExerciseModel.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        db_exercise_to_retry = await self.session.scalar(stmt)

        if db_exercise_to_retry:
            try:
                db_exercise_to_retry.status = (
                    ExerciseStatus.PROCESSING_ERROR_RETRY
                )
                await self.session.flush()
                await self.session.refresh(db_exercise_to_retry)
                logger.info(
                    f'Locked exercise {db_exercise_to_retry.exercise_id} '
                    f'for error retry.'
                )
                return await self._to_entity(db_exercise_to_retry)
            except Exception as e:
                logger.error(
                    f'Failed to lock exercise for retry: {e}', exc_info=True
                )
                # The transaction will be rolled back by the middleware
                return None
        return None

    async def update_exercise_status_and_data(
        self,
        exercise_id: int,
        new_status: ExerciseStatus,
        new_data: Optional[Union[ExerciseData, dict]] = None,
        comments: Optional[str] = None,
    ) -> Optional[Exercise]:
        """
        Updates the status and optionally the data of an exercise.
        """
        db_exercise = await self.session.get(ExerciseModel, exercise_id)
        if db_exercise:
            db_exercise.status = new_status
            if new_data:
                if hasattr(new_data, 'model_dump'):
                    db_exercise.data = new_data.model_dump()
                else:
                    db_exercise.data = new_data
            if comments is not None:
                db_exercise.comments = comments

            await self.session.flush()
            await self.session.refresh(db_exercise)
            return await self._to_entity(db_exercise)
        return None

    async def get_exercise_ids_for_quality_review(
        self,
        min_weighted_attempts_sum_for_review: float,
        weighted_error_threshold: float,
        default_user_rating: float = 0.1,
        min_hours_since_last_update: Optional[int] = None,
    ) -> List[int]:
        """
        Fetches exercise IDs that are candidates for review based on
        weighted error rates, using user ratings from DBUserBotProfile.
        Optionally filters out exercises updated recently.
        """
        updated_at_filter_condition = ''
        if (
            min_hours_since_last_update is not None
            and min_hours_since_last_update > 0
        ):
            updated_at_filter_condition = (
                f'AND e.updated_at <= NOW() '
                f"- INTERVAL '{min_hours_since_last_update} hours'"
            )

        sql_query = f"""
        WITH exercise_weighted_errors AS (
            SELECT
                e.exercise_id,
                SUM(COALESCE(ubp.rating, {default_user_rating}))
                    AS total_rating_sum_for_exercise,
                SUM(
                    CASE
                        WHEN ea.is_correct IS FALSE THEN COALESCE(
                            ubp.rating, {default_user_rating})
                        ELSE 0
                    END
                ) AS incorrect_rating_sum_for_exercise,
                COUNT(ea.attempt_id) as total_raw_attempts
            FROM
                exercises e
            JOIN
                exercise_attempts ea ON e.exercise_id = ea.exercise_id
            LEFT JOIN user_bot_profiles ubp
                ON ea.user_id = ubp.user_id
                    AND e.exercise_language = ubp.bot_id::TEXT
            WHERE
                e.status = '{ExerciseStatus.PUBLISHED.value}'
                {updated_at_filter_condition}
            GROUP BY
                e.exercise_id
        )
        SELECT
            exercise_id
        FROM
            exercise_weighted_errors
        WHERE
            total_rating_sum_for_exercise >=
                {min_weighted_attempts_sum_for_review}
            AND (incorrect_rating_sum_for_exercise
                / NULLIF(total_rating_sum_for_exercise, 0))
                > {weighted_error_threshold};
        """

        result = await self.session.execute(text(sql_query))
        exercise_ids = [row[0] for row in result.fetchall()]
        logger.info(
            f'Found {len(exercise_ids)} exercises '
            f'for quality review based on DB ratings'
            f'{f" (excluding those updated in last "
               f"{min_hours_since_last_update}h)"
            if min_hours_since_last_update else ""}.'
        )
        return exercise_ids

    async def update_statuses(
        self, exercise_ids: list[int], new_status: ExerciseStatus
    ) -> int:
        if not exercise_ids:
            return 0

        stmt = (
            update(ExerciseModel)
            .where(ExerciseModel.exercise_id.in_(exercise_ids))
            .values(status=new_status)
            .execution_options(synchronize_session='fetch')
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_exercises_by_status(
        self, status: ExerciseStatus, limit: Optional[int] = None
    ) -> List[Exercise]:
        stmt = select(ExerciseModel).where(ExerciseModel.status == status)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        db_exercises = result.scalars().all()
        return [await self._to_entity(db_ex) for db_ex in db_exercises]
