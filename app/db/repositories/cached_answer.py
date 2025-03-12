from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.cached_answer import CachedAnswer as CachedAnswerEntity
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.value_objects.answer import Answer
from app.db.models import CachedAnswer as CachedAnswerModel
from app.db.models import ExerciseAttempt as ExerciseAttemptModel


class SQLAlchemyCachedAnswerRepository(CachedAnswerRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, answer_id: int) -> Optional[CachedAnswerEntity]:
        result = await self.session.get(CachedAnswerModel, answer_id)
        if not result:
            return None
        return self._to_entity(result)

    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[CachedAnswerEntity]:
        stmt = select(CachedAnswerModel).where(
            CachedAnswerModel.exercise_id == exercise_id
        )
        result = await self.session.execute(stmt)
        answers = result.scalars().all()
        return [self._to_entity(answer) for answer in answers]

    async def save(
        self, cached_answer: CachedAnswerEntity
    ) -> CachedAnswerEntity:
        db_answer = CachedAnswerModel(
            answer_id=cached_answer.answer_id,
            exercise_id=cached_answer.exercise_id,
            answer=cached_answer.answer.to_dict(),
            answer_text=cached_answer.answer.get_answer_text(),
            is_correct=cached_answer.is_correct,
            feedback=cached_answer.feedback,
            created_at=cached_answer.created_at,
            created_by=cached_answer.created_by,
        )
        self.session.add(db_answer)
        await self.session.commit()
        await self.session.refresh(db_answer)
        return self._to_entity(db_answer)

    async def get_attempts(
        self, answer_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        stmt = select(ExerciseAttemptModel).where(
            ExerciseAttemptModel.cached_answer_id == answer_id
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._attempt_to_entity(attempt) for attempt in attempts]

    async def get_by_exercise_and_answer(
        self, exercise_id: int, answer: Answer
    ) -> Optional[CachedAnswerEntity]:
        stmt = select(CachedAnswerModel).where(
            CachedAnswerModel.exercise_id == exercise_id,
            CachedAnswerModel.answer_text == answer.get_answer_text(),
        )
        result = await self.session.execute(stmt)
        db_answer = result.scalar_one_or_none()
        if not db_answer:
            return None
        return self._to_entity(db_answer)

    def _to_entity(self, db_answer: CachedAnswerModel) -> CachedAnswerEntity:
        return CachedAnswerEntity(
            answer_id=db_answer.answer_id,
            exercise_id=db_answer.exercise_id,
            answer=Answer.from_dict(db_answer.answer),
            is_correct=db_answer.is_correct,
            feedback=db_answer.feedback,
            created_at=db_answer.created_at,
            created_by=db_answer.created_by,
        )

    def _attempt_to_entity(
        self, db_attempt: ExerciseAttemptModel
    ) -> ExerciseAttempt:
        return ExerciseAttempt(
            attempt_id=db_attempt.attempt_id,
            user_id=db_attempt.user_id,
            exercise_id=db_attempt.exercise_id,
            answer=Answer.from_dict(db_attempt.answer),
            is_correct=db_attempt.is_correct,
            feedback=db_attempt.feedback,
            cached_answer_id=db_attempt.cached_answer_id,
        )
