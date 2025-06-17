from typing import Optional, override

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user_report import UserReport as UserReportEntity
from app.core.repositories.user_report import UserReportRepository
from app.db.models.user_report import UserReport as UserReportModel


class SQLAlchemyUserReportRepository(UserReportRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, db_model: UserReportModel) -> UserReportEntity:
        return UserReportEntity.model_validate(db_model)

    def _to_db_model(self, entity: UserReportEntity) -> UserReportModel:
        return UserReportModel(**entity.model_dump(exclude_unset=True))

    @override
    async def create(self, report: UserReportEntity) -> UserReportEntity:
        db_report = self._to_db_model(report)
        self.session.add(db_report)
        await self.session.flush()
        await self.session.refresh(db_report)
        return self._to_entity(db_report)

    @override
    async def get_by_id(self, report_id: int) -> Optional[UserReportEntity]:
        db_report = await self.session.get(UserReportModel, report_id)
        if db_report:
            return self._to_entity(db_report)
        return None
