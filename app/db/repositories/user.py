from typing import Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User as UserEntity
from app.core.repositories.user import UserRepository
from app.db.models.user import User


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        result = await self.session.get(User, user_id)
        if not result:
            return None
        return self._to_entity(result)

    @override
    async def get_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[UserEntity]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return self._to_entity(user)

    @override
    async def save(self, user: UserEntity) -> UserEntity:
        db_user = await self.session.merge(self._to_model(user))
        await self.session.commit()
        await self.session.refresh(db_user)
        return self._to_entity(db_user)

    def _to_model(self, user: UserEntity) -> User:
        return User(
            user_id=user.user_id,
            telegram_id=user.telegram_id,
            name=user.name,
            username=user.username,
            is_active=user.is_active,
        )

    def _to_entity(self, db_user: User) -> UserEntity:
        return UserEntity(
            user_id=db_user.user_id,
            telegram_id=db_user.telegram_id,
            name=db_user.name,
            username=db_user.username,
            is_active=db_user.is_active,
        )
