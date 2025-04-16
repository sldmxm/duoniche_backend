import logging
from typing import Optional

from app.core.entities.user import User
from app.core.repositories.user import UserRepository
from app.metrics import BACKEND_USER_METRICS

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.user_repository.get_by_id(user_id)

    async def get_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        return await self.user_repository.get_by_telegram_id(telegram_id)

    async def update(self, user_id: int, **kwargs) -> User:
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise ValueError(f'User {user_id} does not exist')
        for key, value in kwargs.items():
            if hasattr(existing_user, key):
                setattr(existing_user, key, value)
            else:
                raise ValueError(f'User has no attribute {key}')
        updated_user = await self.user_repository.update(existing_user)
        return updated_user

    async def get_or_create(self, user: User) -> User:
        # TODO: Для дополнительного языка того же пользователя
        #  заводить нового пользователя

        existing_user = await self.user_repository.get_by_telegram_id(
            user.telegram_id
        )
        if existing_user:
            logger.info(f'User tg_id={user.telegram_id} already exists')
            return existing_user
        logger.info(f'User tg_id={user.telegram_id} does not exist.')
        new_user = await self.user_repository.save(user)

        BACKEND_USER_METRICS['new'].labels(
            cohort=new_user.cohort,
            plan=new_user.plan,
            target_language=new_user.target_language,
            user_language=new_user.user_language,
            language_level=new_user.language_level.value,
        ).inc()

        logger.info(f'Created new user {new_user}')
        return new_user
