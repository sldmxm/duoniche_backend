from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

T = TypeVar('T')


class AsyncRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[T]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, entity: T) -> T:
        raise NotImplementedError
