from typing import Optional, override

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise import Exercise as ExerciseEntity
from app.core.entities.user import User as UserEntity
from app.core.repositories.exercise import ExerciseRepository
from app.db.models import Exercise


class SQLAlchemyExerciseRepository(ExerciseRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, exercise_id: int) -> Optional[ExerciseEntity]:
        result = await self.session.get(Exercise, exercise_id)
        if not result:
            return None
        return self._to_entity(result)

    @override
    async def get_new_exercise(
        self,
        user: UserEntity,
        language_level: str,
        exercise_type: str,
    ) -> Optional[ExerciseEntity]:
        # TODO: Написать правильный фцнкционал вместо заглушки
        return await self.get_by_id(1)

    @override
    async def get_exercise_for_repetition(
        self,
        user: UserEntity,
        language_level: str,
        exercise_type: str,
    ) -> Optional[ExerciseEntity]:
        # TODO: Написать правильный фцнкционал вместо заглушки
        return await self.get_by_id(1)

    @override
    async def save(self, exercise: ExerciseEntity) -> ExerciseEntity:
        db_exercise = await self.session.merge(self._to_model(exercise))
        await self.session.commit()
        await self.session.refresh(db_exercise)
        return self._to_entity(db_exercise)

    def _to_model(self, exercise: ExerciseEntity) -> Exercise:
        return Exercise(
            exercise_id=exercise.exercise_id,
            exercise_type=exercise.exercise_type,
            language_level=exercise.language_level,
            topic=exercise.topic,
            exercise_text=exercise.exercise_text,
            data=exercise.data,
        )

    def _to_entity(self, db_exercise: Exercise) -> ExerciseEntity:
        return ExerciseEntity(
            exercise_id=db_exercise.exercise_id,
            exercise_type=db_exercise.exercise_type,
            language_level=db_exercise.language_level,
            topic=db_exercise.topic,
            exercise_text=db_exercise.exercise_text,
            data=db_exercise.data,
        )
