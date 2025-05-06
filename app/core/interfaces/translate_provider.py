from abc import ABC, abstractmethod


class TranslateProvider(ABC):
    @abstractmethod
    async def translate_text(self, text: str, target_language: str) -> str:
        pass

    @abstractmethod
    async def translate_feedback(
        self,
        feedback: str,
        user_language: str,
        exercise_data: str,
        user_answer: str,
        exercise_language: str,
    ) -> str:
        pass
