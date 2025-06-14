import logging
from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User as UserCore
from app.core.repositories.user import UserRepository
from app.db.models.user import User as UserDBModel

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def get_by_id(self, user_id: int) -> Optional[UserCore]:
        db_user = await self.session.get(UserDBModel, user_id)
        if not db_user:
            return None
        return UserCore.model_validate(db_user)

    @override
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[UserCore]:
        stmt = select(UserDBModel).where(
            UserDBModel.telegram_id == telegram_id
        )
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        if not db_user:
            return None
        return UserCore.model_validate(db_user)

    @override
    async def get_all(self) -> List[UserCore]:
        stmt = select(UserDBModel)
        result = await self.session.execute(stmt)
        db_users = result.scalars().all()
        return [UserCore.model_validate(db_user) for db_user in db_users]

    @override
    async def update(self, user: UserCore) -> UserCore:
        if user.user_id is None:
            raise ValueError('User ID must be provided for an update.')
        db_user = await self.session.get(UserDBModel, user.user_id)
        if not db_user:
            raise ValueError(f'User with id {user.user_id} does not exist')

        update_data = user.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == 'user_id':
                continue
            if hasattr(db_user, key):
                setattr(db_user, key, value)
            else:
                logger.warning(
                    f"Attempted to update non-existent field '{key}' "
                    f'on UserDBModel for user_id {user.user_id}'
                )

        await self.session.flush()
        await self.session.refresh(db_user)
        return UserCore.model_validate(db_user)

    @override
    async def create(self, user: UserCore) -> UserCore:
        user_data = user.model_dump(exclude_unset=True)
        db_user = UserDBModel(**user_data)
        self.session.add(db_user)
        await self.session.flush()
        await self.session.refresh(db_user)
        return UserCore.model_validate(db_user)
