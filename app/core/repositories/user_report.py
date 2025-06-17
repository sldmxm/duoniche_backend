from abc import ABC, abstractmethod
from typing import Optional

from app.core.entities.user_report import UserReport


class UserReportRepository(ABC):
    """
    Abstract base class for user report data persistence.
    """

    @abstractmethod
    async def create(self, report: UserReport) -> UserReport:
        """
        Creates a new user report record.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, report_id: int) -> Optional[UserReport]:
        """
        Retrieves a user report by its ID.
        """
