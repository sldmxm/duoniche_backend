from typing import Optional, override

from sqlalchemy import select
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

    @override
    async def get_latest_by_user_and_bot(
        self, user_id: int, bot_id: str
    ) -> Optional[UserReportEntity]:
        stmt = (
            select(UserReportModel)
            .where(
                UserReportModel.user_id == user_id,
                UserReportModel.bot_id == bot_id,
            )
            .order_by(UserReportModel.week_start_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        db_report = result.scalar_one_or_none()
        if db_report:
            return self._to_entity(db_report)
        return None

    @override
    async def update(self, report: UserReportEntity) -> UserReportEntity:
        db_report = await self.session.get(UserReportModel, report.report_id)
        if not db_report:
            raise ValueError(f'Report with id {report.report_id} not found.')

        update_data = report.model_dump(
            exclude={'report_id', 'user_id', 'bot_id', 'week_start_date'}
        )
        for key, value in update_data.items():
            setattr(db_report, key, value)
        await self.session.flush()
        return self._to_entity(db_report)
