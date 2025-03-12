from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.repositories.exercise import ExerciseRepository
from app.db.models import Exercise as ExerciseModel


class SQLAlchemyExerciseRepository(ExerciseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, exercise_id: int) -> Optional[Exercise]:
        result = await self.session.get(ExerciseModel, exercise_id)
        if not result:
            return None
        return self._to_entity(result)

    @override
    async def get_all(self) -> List[Exercise]:
        stmt = select(ExerciseModel)
        result = await self.session.execute(stmt)
        exercises = result.scalars().all()
        return [self._to_entity(exercise) for exercise in exercises]

    @override
    async def save(self, exercise: Exercise) -> Exercise:
        db_exercise = ExerciseModel(
            exercise_id=exercise.exercise_id,
            exercise_type=exercise.exercise_type,
            language_level=exercise.language_level,
            topic=exercise.topic,
            exercise_text=exercise.exercise_text,
            data=exercise.data.to_dict(),
        )
        self.session.add(db_exercise)
        await self.session.commit()
        await self.session.refresh(db_exercise)
        return self._to_entity(db_exercise)

    @override
    async def get_new_exercise(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Optional[Exercise]:
        stmt = select(ExerciseModel).where(
            ExerciseModel.language_level == language_level,
            ExerciseModel.exercise_type == exercise_type,
        )
        result = await self.session.execute(stmt)
        db_exercise = result.scalar_one_or_none()
        if not db_exercise:
            return None
        return self._to_entity(db_exercise)

    @override
    async def get_exercise_for_repetition(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Optional[Exercise]:
        # TODO: add logic
        return None

    def _to_entity(self, db_exercise: ExerciseModel) -> Exercise:
        return Exercise(
            exercise_id=db_exercise.exercise_id,
            exercise_type=db_exercise.exercise_type,
            language_level=db_exercise.language_level,
            topic=db_exercise.topic,
            exercise_text=db_exercise.exercise_text,
            data=Exercise.get_data_from_dict(db_exercise.data),
        )
