from datetime import datetime
from typing import Dict, List, Optional, override

from sqlalchemy import bindparam, select, text
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
        self,
        attempt_id: int,
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
        self,
        user_id: int,
        exercise_id: int,
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
        self,
        user_id: int,
    ) -> List[ExerciseAttemptEntity]:
        stmt = select(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        attempts = result.scalars().all()
        return [self._to_entity(attempt) for attempt in attempts]

    @override
    async def get_by_exercise_id(
        self,
        exercise_id: int,
    ) -> List[ExerciseAttemptEntity]:
        stmt = select(ExerciseAttempt).where(
            ExerciseAttempt.exercise_id == exercise_id,
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
        error_tags: Optional[dict] = None,
    ) -> ExerciseAttemptEntity:
        attempt = await self.session.get(ExerciseAttempt, attempt_id)
        if not attempt:
            raise ValueError('Attempt does not exist')
        attempt.is_correct = is_correct
        attempt.feedback = feedback
        attempt.answer_id = answer_id
        attempt.error_tags = error_tags
        await self.session.flush()
        await self.session.refresh(attempt)
        return self._to_entity(attempt)

    @override
    async def create(
        self,
        exercise_attempt: ExerciseAttemptEntity,
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

    @override
    async def get_period_summary_for_user_and_bot(
        self,
        user_id: int,
        bot_id: str,
        start_date: datetime,
    ) -> Dict:
        query = text(
            """
            WITH weekly_attempts AS (
                SELECT
                    ea.is_correct,
                    e.grammar_tags,
                    ea.error_tags
                FROM
                    exercise_attempts ea
                JOIN
                    exercises e ON ea.exercise_id = e.exercise_id
                WHERE
                    ea.user_id = :user_id
                    AND e.exercise_language = :bot_id
                    AND ea.created_at >= :start_date
            )
            SELECT
                COUNT(*) AS total_attempts,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
                    AS correct_attempts,
                (SELECT jsonb_object_agg(tag, count) FROM (
                    SELECT
                    jsonb_array_elements_text(grammar_tags->'grammar') AS tag,
                    COUNT(*) as count
                    FROM weekly_attempts
                    WHERE grammar_tags->'grammar' IS NOT NULL
                    GROUP BY tag ORDER BY count DESC
                ) AS grammar_summary) AS grammar_tags,
                (SELECT jsonb_object_agg(tag, count) FROM (
                    SELECT
                    jsonb_array_elements_text(grammar_tags->'vocabulary')
                        AS tag, COUNT(*) as count
                    FROM weekly_attempts
                    WHERE grammar_tags->'vocabulary' IS NOT NULL
                    GROUP BY tag ORDER BY count DESC
                ) AS vocab_summary) AS vocab_tags,
                (SELECT jsonb_object_agg(tag, count) FROM (
                    SELECT
                    jsonb_array_elements_text(error_tags->'grammar') AS tag,
                    COUNT(*) as count
                    FROM weekly_attempts
                    WHERE is_correct = false
                        AND error_tags->'grammar' IS NOT NULL
                    GROUP BY tag ORDER BY count DESC
                ) AS error_grammar_tags,
                (SELECT jsonb_object_agg(tag, count) FROM (
                    SELECT jsonb_array_elements_text(error_tags->'vocabulary')
                        AS tag, COUNT(*) as count
                    FROM weekly_attempts
                    WHERE is_correct = false
                        AND error_tags->'vocabulary' IS NOT NULL
                    GROUP BY tag ORDER BY count DESC
                ) AS error_vocab_tags)
            FROM
                weekly_attempts;
            """,
        ).bindparams(
            bindparam('user_id', value=user_id),
            bindparam('bot_id', value=bot_id),
            bindparam('start_date', value=start_date),
        )

        result = await self.session.execute(query)
        summary = result.fetchone()

        if not summary or summary[0] is None:
            return {}

        return {
            'total_attempts': summary[0] or 0,
            'correct_attempts': summary[1] or 0,
            'grammar_tags': summary[2] or {},
            'vocab_tags': summary[3] or {},
            'error_grammar_tags': summary[4] or {},
            'error_vocab_tags': summary[5] or {},
        }
