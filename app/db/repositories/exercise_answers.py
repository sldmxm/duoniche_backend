from typing import List, Optional, override

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.entities.exercise_answer import (
    ExerciseAnswer as ExerciseAnswerEntity,
)
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.value_objects.answer import Answer, create_answer_model_validate
from app.db.models import ExerciseAnswer as ExerciseAnswerModel
from app.db.models import ExerciseAttempt as ExerciseAttemptModel


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

    async def create(
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
        await self.session.flush()
        await self.session.refresh(db_answer)
        return self._to_entity(db_answer)

    async def get_all_by_user_answer(
        self,
        exercise_id: int,
        answer: Answer,
    ) -> List[ExerciseAnswerEntity]:
        stmt = select(ExerciseAnswerModel).where(
            ExerciseAnswerModel.exercise_id == exercise_id,
            ExerciseAnswerModel.answer_text == answer.get_answer_text(),
        )
        result = await self.session.execute(stmt)
        db_answers = result.scalars().all()
        if not db_answers:
            return []
        return [self._to_entity(answer) for answer in db_answers]

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

    async def get_answers_with_attempt_counts(
        self, exercise_id: int
    ) -> List[tuple[ExerciseAnswerEntity, int]]:
        """
        Fetches all ExerciseAnswerEntities for a given exercise_id,
        along with the count of attempts associated with each answer_id.
        Returns a list of tuples: (ExerciseAnswerEntity, attempt_count).
        """
        ea_attempt_alias = aliased(ExerciseAttemptModel)

        stmt = (
            select(
                ExerciseAnswerModel,
                func.count(ea_attempt_alias.attempt_id).label('attempt_count'),
            )
            .outerjoin(
                ea_attempt_alias,
                ExerciseAnswerModel.answer_id == ea_attempt_alias.answer_id,
            )
            .where(ExerciseAnswerModel.exercise_id == exercise_id)
            .group_by(ExerciseAnswerModel.answer_id)
        )

        result = await self.session.execute(stmt)

        answers_with_counts: List[tuple[ExerciseAnswerEntity, int]] = []
        for db_answer, count in result.all():
            answers_with_counts.append((self._to_entity(db_answer), count))

        return answers_with_counts
