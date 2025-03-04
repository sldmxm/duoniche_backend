from sqlalchemy import Boolean, Column, Integer, String

from app.db.models.base import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String)
    username = Column(String)
    is_active = Column(Boolean, default=True)
    language_level = Column(String, default='beginner')
