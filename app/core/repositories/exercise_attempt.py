from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from app.core.entities.exercise_attempt import (
    ExerciseAttempt,
    IncorrectAttemptDetail,
)


class ExerciseAttemptRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attempt_id: int) -> Optional[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> List[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_exercise(
        self, user_id: int, exercise_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id(
        self, user_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self, exercise_attempt: ExerciseAttempt
    ) -> ExerciseAttempt:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        attempt_id: int,
        is_correct: bool,
        feedback: Optional[str],
        answer_id: int,
        error_tags: Optional[dict] = None,
    ) -> ExerciseAttempt:
        raise NotImplementedError

    @abstractmethod
    async def get_period_summary_for_user_and_bot(
        self,
        user_id: int,
        bot_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """
        Aggregates user's performance data over the last week.
        """

    @abstractmethod
    async def get_incorrect_attempts_with_details(
        self,
        user_id: int,
        bot_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 3,
    ) -> List[IncorrectAttemptDetail]:
        raise NotImplementedError
