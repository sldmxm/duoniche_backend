from datetime import datetime
from typing import TYPE_CHECKING, Dict

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class DBPayment(Base):
    __tablename__ = 'payments'

    payment_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.user_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_payload: Mapped[str] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default='session_unlock'
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    raw_payment_data: Mapped[Dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped['User'] = relationship(back_populates='payments')

    def __repr__(self) -> str:
        return (
            f'<DBPayment(payment_id={self.payment_id}, '
            f'user_id={self.user_id}, '
            f'charge_id="{self.telegram_payment_charge_id}")>'
        )
