from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise_answer import (
    ExerciseAnswer as ExerciseAnswerEntity,
)
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.value_objects.answer import Answer, create_answer_model_validate
from app.db.models import ExerciseAnswer as ExerciseAnswerModel


class SQLAlchemyExerciseAnswerRepository(ExerciseAnswerRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(
        self, answer_id: int
    ) -> Optional[ExerciseAnswerEntity]:
        result = await self.session.get(ExerciseAnswerModel, answer_id)
        if not result:
            return None
        return self._to_entity(result)

    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAnswerEntity]:
        stmt = select(ExerciseAnswerModel).where(
            ExerciseAnswerModel.exercise_id == exercise_id
        )
        result = await self.session.execute(stmt)
        answers = result.scalars().all()
        return [self._to_entity(answer) for answer in answers]

    async def get_correct_answers_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAnswerEntity]:
        stmt = select(ExerciseAnswerModel).where(
            ExerciseAnswerModel.exercise_id == exercise_id,
            ExerciseAnswerModel.is_correct,
        )
        result = await self.session.execute(stmt)
        answers = result.scalars().all()
        return [self._to_entity(answer) for answer in answers]

    async def save(
        self, exercise_answers: ExerciseAnswerEntity
    ) -> ExerciseAnswerEntity:
        db_answer = ExerciseAnswerModel(
            answer_id=exercise_answers.answer_id,
            exercise_id=exercise_answers.exercise_id,
            answer=exercise_answers.answer.model_dump(),
            answer_text=exercise_answers.answer.get_answer_text(),
            is_correct=exercise_answers.is_correct,
            feedback=exercise_answers.feedback,
            feedback_language=exercise_answers.feedback_language,
            created_at=exercise_answers.created_at,
            created_by=exercise_answers.created_by,
        )
        self.session.add(db_answer)
        await self.session.commit()
        await self.session.refresh(db_answer)
        return self._to_entity(db_answer)

    async def get_by_exercise_and_answer(
        self,
        exercise_id: int,
        answer: Answer,
        language: str,
    ) -> Optional[ExerciseAnswerEntity]:
        stmt = select(ExerciseAnswerModel).where(
            ExerciseAnswerModel.exercise_id == exercise_id,
            ExerciseAnswerModel.answer_text == answer.get_answer_text(),
            ExerciseAnswerModel.feedback_language == language,
        )
        result = await self.session.execute(stmt)
        db_answer = result.scalar_one_or_none()
        if not db_answer:
            return None
        return self._to_entity(db_answer)

    def _to_entity(
        self, db_answer: ExerciseAnswerModel
    ) -> ExerciseAnswerEntity:
        return ExerciseAnswerEntity(
            answer_id=db_answer.answer_id,
            exercise_id=db_answer.exercise_id,
            answer=create_answer_model_validate(db_answer.answer),
            is_correct=db_answer.is_correct,
            feedback=db_answer.feedback,
            feedback_language=db_answer.feedback_language,
            created_at=db_answer.created_at,
            created_by=db_answer.created_by,
        )
