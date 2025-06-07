import logging
from typing import Optional, Tuple

from app.core.entities.user import User
from app.core.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.user_repository.get_by_id(user_id)

    async def get_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        return await self.user_repository.get_by_telegram_id(telegram_id)

    async def update(self, user_id: int, **fields_to_update) -> User:
        existing_user = await self.user_repository.get_by_id(user_id)
        if not existing_user:
            raise ValueError(f'User {user_id} does not exist')

        if not fields_to_update:
            return existing_user

        ALLOWED_FIELDS = {
            'username',
            'name',
            'telegram_data',
            'status',
            'status_expires_at',
            'status_source',
            'custom_settings',
        }

        is_changed = False
        for key, value in fields_to_update.items():
            if key in ALLOWED_FIELDS and hasattr(existing_user, key):
                if getattr(existing_user, key) != value:
                    setattr(existing_user, key, value)
                    is_changed = True
            else:
                logger.error(f"Unknown field '{key}' while updating user.")

        if is_changed:
            try:
                updated_user = await self.user_repository.update(existing_user)
                return updated_user
            except Exception as e:
                logger.error(f'Error updating user: {user_id}: {e}')
                raise
        else:
            return existing_user

    async def get_or_create(self, user: User) -> Tuple[User, bool]:
        is_created = False
        existing_user = await self.user_repository.get_by_telegram_id(
            user.telegram_id
        )
        if existing_user:
            logger.info(f'User tg_id={user.telegram_id} already exists')
            return existing_user, is_created

        logger.info(f'User tg_id={user.telegram_id} does not exist.')
        new_user = await self.user_repository.create(user)
        is_created = True

        logger.info(f'Created new user {new_user}')
        return new_user, is_created
