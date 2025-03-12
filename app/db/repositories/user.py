from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.core.repositories.user import UserRepository
from app.db.models.user import User as UserModel


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.get(UserModel, user_id)
        if not result:
            return None
        return self._to_entity(result)

    @override
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        return self._to_entity(db_user)

    @override
    async def get_all(self) -> List[User]:
        stmt = select(UserModel)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        return [self._to_entity(user) for user in users]

    @override
    async def save(self, user: User) -> User:
        db_user = UserModel(
            user_id=user.user_id,
            telegram_id=user.telegram_id,
            username=user.username,
            name=user.name,
            user_language=user.user_language,
            target_language=user.target_language,
        )
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return self._to_entity(db_user)

    def _to_entity(self, db_user: UserModel) -> User:
        return User(
            user_id=db_user.user_id,
            telegram_id=db_user.telegram_id,
            username=db_user.username,
            name=db_user.name,
            user_language=db_user.user_language,
            target_language=db_user.target_language,
        )
