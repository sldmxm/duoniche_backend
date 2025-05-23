import logging
from typing import Optional, override

from sqlalchemy import and_, exists, func, literal, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.repositories.exercise import ExerciseRepository
from app.db.models import Exercise as ExerciseModel
from app.db.models import ExerciseAttempt as ExerciseAttemptModel

logger = logging.getLogger(__name__)


class SQLAlchemyExerciseRepository(ExerciseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _to_entity(self, db_exercise: ExerciseModel) -> Exercise:
        """Converts an ExerciseModel to an Exercise entity."""
        return Exercise(
            exercise_id=db_exercise.exercise_id,
            exercise_type=ExerciseType(db_exercise.exercise_type),
            exercise_language=db_exercise.exercise_language,
            language_level=LanguageLevel(db_exercise.language_level),
            topic=ExerciseTopic(db_exercise.topic),
            exercise_text=db_exercise.exercise_text,
            data=Exercise.get_data_model_validate(db_exercise.data),
        )

    async def _to_db_model(self, exercise: Exercise) -> ExerciseModel:
        """Converts an Exercise entity to an ExerciseModel."""
        return ExerciseModel(
            exercise_id=exercise.exercise_id,
            exercise_type=exercise.exercise_type.value,
            exercise_language=exercise.exercise_language,
            language_level=exercise.language_level.value,
            topic=exercise.topic.value,
            exercise_text=exercise.exercise_text,
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
                not_(ExerciseAttemptModel.is_correct),
            )
        )

        stmt = (
            select(ExerciseModel)
            .where(
                and_(
                    ExerciseModel.exercise_language == target_language,
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
        await self.session.commit()
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
            .where(not_(exists(attempts_exist)))
            .group_by(
                ExerciseModel.exercise_language, ExerciseModel.exercise_type
            )
        )

        result = await self.session.execute(stmt)

        counts: dict[str, dict[str, int]] = {}
        for lang, ex_type, count in result:
            counts.setdefault(lang, {})[ex_type] = count

        return counts
