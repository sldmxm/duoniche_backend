import logging
from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.core.repositories.user import UserRepository
from app.db.models.user import User as UserModel

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, user_id: int) -> Optional[User]:
        db_user = await self.session.get(UserModel, user_id)
        if not db_user:
            return None
        return User.model_validate(db_user.__dict__)

    @override
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        return User.model_validate(db_user.__dict__)

    @override
    async def get_all(self) -> List[User]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        return [User.model_validate(user.__dict__) for user in users]

    @override
    async def save(self, user: User) -> User:
        db_user = UserModel(**user.model_dump())
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return User.model_validate(db_user.__dict__)
