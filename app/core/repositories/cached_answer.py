from abc import abstractmethod
from typing import List, Optional

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.repositories.base import AsyncRepository
from app.core.value_objects.answer import Answer


class CachedAnswerRepository(AsyncRepository[CachedAnswer]):
    @abstractmethod
    async def get_by_id(self, answer_id: int) -> Optional[CachedAnswer]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_id(self, exercise_id: int) -> List[CachedAnswer]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, cached_answer: CachedAnswer) -> CachedAnswer:
        raise NotImplementedError

    @abstractmethod
    async def get_attempts(
        self, answer_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_and_answer(
        self, exercise_id: int, answer: Answer
    ) -> Optional[CachedAnswer]:
        raise NotImplementedError
