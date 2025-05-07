from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar('T')


class AsyncRepository(ABC, Generic[T]):
    @abstractmethod
    async def save(self, entity: T) -> T:
        raise NotImplementedError
