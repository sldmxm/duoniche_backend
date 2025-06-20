from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.enums import ReportStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class UserReport(Base):
    __tablename__ = 'user_reports'

    report_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.user_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    week_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    short_report: Mapped[str] = mapped_column(Text, nullable=False)
    full_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        server_default=ReportStatus.PENDING.value,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped['User'] = relationship(back_populates='reports')

    def __repr__(self) -> str:
        return (
            f'<UserReport(report_id={self.report_id}, '
            f'user_id={self.user_id}, bot_id={self.bot_id}, '
            f'week_start_date={self.week_start_date})>'
        )
