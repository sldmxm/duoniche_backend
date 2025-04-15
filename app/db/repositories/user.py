import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, override

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.user import User
from app.core.enums import LanguageLevel
from app.core.repositories.user import UserRepository
from app.db.models.user import User as UserModel

logger = logging.getLogger(__name__)


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, db_user: UserModel) -> User:
        """Converts a UserModel to a User entity."""
        user_data = db_user.__dict__
        user_data['language_level'] = LanguageLevel(
            user_data['language_level']
        )
        return User.model_validate(user_data)

    def _to_db_model(self, user: User) -> UserModel:
        """Converts a User entity to a UserModel."""
        user_data = user.model_dump()
        user_data['language_level'] = user.language_level.value
        return UserModel(**user_data)

    @override
    async def get_by_id(self, user_id: int) -> Optional[User]:
        db_user = await self.session.get(UserModel, user_id)
        if not db_user:
            return None
        return self._to_entity(db_user)

    @override
    async def get_by_telegram_id(self, telegram_id: str) -> Optional[User]:
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
        db_users = result.scalars().all()
        return [self._to_entity(db_user) for db_user in db_users]

    @override
    async def update(self, user: User) -> User:
        db_user = await self.session.get(UserModel, user.user_id)
        if not db_user:
            raise ValueError('User does not exist')

        update_data = {
            key: value
            for key, value in self._to_db_model(user).__dict__.items()
            if not key.startswith('_') and key != 'user_id'
        }
        for key, value in update_data.items():
            setattr(db_user, key, value)
        await self.session.commit()
        return self._to_entity(db_user)

    @override
    async def save(self, user: User) -> User:
        db_user = self._to_db_model(user)
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return self._to_entity(db_user)

    @override
    async def get_users_with_exercise_lately(
        self, period_seconds: int
    ) -> List[User]:
        now = datetime.now(timezone.utc)
        stmt = select(UserModel).where(
            UserModel.last_exercise_at.isnot(None),
            (
                UserModel.last_exercise_at
                >= now - timedelta(seconds=period_seconds)
            ),
        )
        result = await self.session.execute(stmt)
        db_users = result.scalars().all()
        return [self._to_entity(db_user) for db_user in db_users]
