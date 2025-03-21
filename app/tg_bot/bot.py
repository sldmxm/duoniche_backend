import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from aiohttp import web
from dotenv import load_dotenv
from redis import asyncio as aioredis

from app.api.schemas.user import UserCreate
from app.config import settings
from app.logging_config import configure_logging
from app.tg_bot.utils import UserMiddleware

load_dotenv()
DEBUG = settings.debug.lower() == 'true'
TELEGRAM_TOKEN = settings.telegram_token
USE_WEBHOOK = settings.use_webhook.lower() == 'true'
WEBHOOK_SECRET = settings.webhook_secret
BASE_WEBHOOK_URL = settings.base_webhook_url
WEBHOOK_PATH = settings.webhook_path
WEBAPP_HOST = settings.webapp_host
WEBAPP_PORT = settings.webapp_port
REDIS_URL = settings.redis_url
API_URL = settings.api_url

configure_logging()
logger = logging.getLogger(__name__)

# async def set_bot_command(bot: Bot):
#     await bot.set_my_commands(
#         [
#             BotCommand(
#                 command=command.command, description=command.description
#             )
#             for command in BotCommandList.COMMANDS
#         ]
#     )


async def on_startup(bot: Bot) -> None:
    logger.info('Drop pending updates')
    await bot.delete_webhook(drop_pending_updates=True)
    if USE_WEBHOOK:
        await bot.set_webhook(
            f'{BASE_WEBHOOK_URL}{WEBHOOK_PATH}',
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
    # await set_bot_command(bot=bot)


async def on_shutdown(bot: Bot) -> None:
    logger.info('Deleting webhook')
    await bot.delete_webhook(drop_pending_updates=True)


def start_webhook_bot(dp: Dispatcher, bot: Bot):
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    logger.info(f'Webhook server running on {WEBAPP_HOST}:{WEBAPP_PORT}')
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)


async def start_pooling_bot(dp: Dispatcher, bot: Bot):
    logger.info('Starting pulling')
    await dp.start_polling(bot)


router = Router()


async def register_user(message: Message):
    async with httpx.AsyncClient() as client:
        user_data = UserCreate(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            name=message.from_user.full_name,
            user_language=message.from_user.language_code,
            target_language=message.from_user.language_code,
        )
        response = await client.put(
            f'{API_URL}/api/v1/users/', json=user_data.model_dump()
        )
        response.raise_for_status()
        return response.json()


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await register_user(message)
    await message.answer(f'Hello, {message.from_user.full_name}!')


@router.message(F.text)
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types
    (like text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer('Nice try!')


def main():
    logger.info('Starting bot')

    redis = aioredis.from_url(REDIS_URL)
    storage = RedisStorage(
        redis=redis,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        state_ttl=60 * 60 * 24,
        data_ttl=60 * 60 * 24,
    )
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )
    dp = Dispatcher(
        bot=bot,
        storage=storage,
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.message.middleware(UserMiddleware())

    dp.include_routers(
        router,
        #     add_offer_dialog,
        #     deal_feedback_dialog,
    )
    # setup_dialogs(dp)
    # dp.include_routers(
    #     main_menu.router,
    #     start.router,
    #     inline.router,
    #     offers_list.router,
    #     deals_list.router,
    #     deal.router,
    #     other.router,
    # )

    if USE_WEBHOOK:
        start_webhook_bot(dp=dp, bot=bot)
    else:
        asyncio.run(start_pooling_bot(dp=dp, bot=bot))

    logger.info('Bot stopped')


if __name__ == '__main__':
    main()
