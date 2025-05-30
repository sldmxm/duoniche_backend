from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ExerciseStatus
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exercise_answer import ExerciseAnswer
    from app.db.models.exercise_attempt import ExerciseAttempt


class Exercise(Base):
    __tablename__ = 'exercises'

    exercise_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    exercise_type: Mapped[str] = mapped_column(String, nullable=False)
    exercise_language: Mapped[str] = mapped_column(String, nullable=False)
    language_level: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    exercise_text: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, nullable=False
    )
    status: Mapped[ExerciseStatus] = mapped_column(
        SQLAlchemyEnum(
            ExerciseStatus,
            name='exercise_status_enum',
            create_type=True,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
        server_default=ExerciseStatus.PUBLISHED.value,
        index=True,
    )

    attempts: Mapped[list['ExerciseAttempt']] = relationship(
        back_populates='exercise', cascade='all, delete-orphan'
    )
    exercise_answers: Mapped[list['ExerciseAnswer']] = relationship(
        back_populates='exercise', cascade='all, delete-orphan'
    )
