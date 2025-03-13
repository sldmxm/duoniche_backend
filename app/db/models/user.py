from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    username = Column(String)
    name = Column(String)
    user_language = Column(String)
    target_language = Column(String)
    language_level = Column(String, default='beginner')
