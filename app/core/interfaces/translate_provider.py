from abc import ABC, abstractmethod


class TranslateProvider(ABC):
    @abstractmethod
    async def translate_text(self, text: str, target_language: str) -> str:
        pass
