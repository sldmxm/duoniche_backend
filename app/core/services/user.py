from app.core.entities.user import User
from app.core.repositories.user import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return self.user_repository.get_by_telegram_id(telegram_id)

    def save_user(self, user: User) -> User:
        return self.user_repository.save(user)
