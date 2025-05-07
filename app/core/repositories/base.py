from abc import ABC
from typing import Generic, TypeVar

T = TypeVar('T')


class AsyncRepository(ABC, Generic[T]):
    pass
