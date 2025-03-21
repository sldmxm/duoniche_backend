from typing import Any, Callable

import httpx
from aiogram import BaseMiddleware
from aiogram.types import Message

from app.config import settings

API_URL = settings.api_url


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Any],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.text == '/start':
            return await handler(event, data)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{API_URL}/api/v1/users/{event.from_user.id}'
            )
            if response.status_code == 404:
                await event.answer('Please use /start command')
                return
            response.raise_for_status()
            data['user'] = response.json()
            return await handler(event, data)
