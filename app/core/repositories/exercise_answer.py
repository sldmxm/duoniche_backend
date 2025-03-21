from abc import abstractmethod
from typing import List, Optional

from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.repositories.base import AsyncRepository
from app.core.value_objects.answer import Answer


class ExerciseAnswerRepository(AsyncRepository[ExerciseAnswer]):
    @abstractmethod
    async def get_by_id(self, answer_id: int) -> Optional[ExerciseAnswer]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAnswer]:
        raise NotImplementedError

    @abstractmethod
    async def get_correct_answers_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAnswer]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, exercise_answers: ExerciseAnswer) -> ExerciseAnswer:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_and_answer(
        self, exercise_id: int, answer: Answer
    ) -> Optional[ExerciseAnswer]:
        raise NotImplementedError
