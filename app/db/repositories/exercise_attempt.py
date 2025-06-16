from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise_attempt import (
    ExerciseAttempt as ExerciseAttemptEntity,
)
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.value_objects.answer import create_answer_model_validate
from app.db.models import ExerciseAttempt


class SQLAlchemyExerciseAttemptRepository(ExerciseAttemptRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(
        self, attempt_id: int
    ) -> Optional[ExerciseAttemptEntity]:
        result = await self.session.get(ExerciseAttempt, attempt_id)
        if not result:
            return None
        return self._to_entity(result)

    @override
    async def get_all(self) -> List[ExerciseAttemptEntity]:
        stmt = select(ExerciseAttempt)
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._to_entity(attempt) for attempt in attempts]

    @override
    async def get_by_user_and_exercise(
        self, user_id: int, exercise_id: int
    ) -> Optional[List[ExerciseAttemptEntity]]:
        stmt = select(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user_id,
            ExerciseAttempt.exercise_id == exercise_id,
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._to_entity(attempt) for attempt in attempts]

    @override
    async def get_by_user_id(
        self, user_id: int
    ) -> List[ExerciseAttemptEntity]:
        stmt = select(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user_id
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._to_entity(attempt) for attempt in attempts]

    @override
    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAttemptEntity]:
        stmt = select(ExerciseAttempt).where(
            ExerciseAttempt.exercise_id == exercise_id
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._to_entity(attempt) for attempt in attempts]

    @override
    async def update(
        self,
        attempt_id: int,
        is_correct: bool,
        feedback: Optional[str],
        answer_id: int,
    ) -> ExerciseAttemptEntity:
        attempt = await self.session.get(ExerciseAttempt, attempt_id)
        if not attempt:
            raise ValueError('Attempt does not exist')
        attempt.is_correct = is_correct
        attempt.feedback = feedback
        attempt.answer_id = answer_id
        await self.session.flush()
        await self.session.refresh(attempt)
        return self._to_entity(attempt)

    @override
    async def create(
        self, exercise_attempt: ExerciseAttemptEntity
    ) -> ExerciseAttemptEntity:
        db_attempt = ExerciseAttempt(
            attempt_id=exercise_attempt.attempt_id,
            user_id=exercise_attempt.user_id,
            exercise_id=exercise_attempt.exercise_id,
            answer=exercise_attempt.answer.model_dump(),
            is_correct=exercise_attempt.is_correct,
            feedback=exercise_attempt.feedback,
            answer_id=exercise_attempt.answer_id,
            error_tags=exercise_attempt.error_tags,
        )
        self.session.add(db_attempt)
        await self.session.flush()
        await self.session.refresh(db_attempt)
        return self._to_entity(db_attempt)

    def _to_entity(self, db_attempt: ExerciseAttempt) -> ExerciseAttemptEntity:
        return ExerciseAttemptEntity(
            attempt_id=db_attempt.attempt_id,
            user_id=db_attempt.user_id,
            exercise_id=db_attempt.exercise_id,
            answer=create_answer_model_validate(db_attempt.answer),
            is_correct=db_attempt.is_correct,
            feedback=db_attempt.feedback,
            error_tags=db_attempt.error_tags,
            answer_id=db_attempt.answer_id,
        )
