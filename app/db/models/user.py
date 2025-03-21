from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)
    user_language = Column(String, nullable=True)
    target_language = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    language_level = Column(String, default='beginner')
