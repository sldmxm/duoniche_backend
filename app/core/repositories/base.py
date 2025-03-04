from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

T = TypeVar('T')


class AsyncRepository(ABC, Generic[T]):
    """Base class for async repositories"""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, entity: T) -> T:
        raise NotImplementedError
