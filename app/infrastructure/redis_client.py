import logging
from typing import Optional

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[AsyncRedis] = None


async def get_redis_client() -> AsyncRedis:
    """
    Provides a singleton instance of the asynchronous Redis client.
    Initializes the client on first call.
    """
    global _redis_client
    if _redis_client is None:
        logger.info(f'Initializing Redis client for URL: {settings.redis_url}')
        try:
            _redis_client = AsyncRedis.from_url(
                settings.redis_url, decode_responses=False
            )
            await _redis_client.ping()
            logger.info('Successfully connected to Redis.')
        except RedisError as e:
            logger.error(f'Failed to connect to Redis: {e}')
            raise
    return _redis_client


async def close_redis_client() -> None:
    """
    Closes the Redis client connection if it was initialized.
    """
    global _redis_client
    if _redis_client:
        logger.info('Closing Redis client connection.')
        try:
            await _redis_client.close()
            logger.info('Redis client connection closed.')
        except RedisError as e:
            logger.error(f'Error closing Redis connection: {e}')
        finally:
            _redis_client = None
