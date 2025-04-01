import asyncio
import logging
from typing import Any, Callable, Coroutine, Generic, Optional, TypeVar

from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')
Serializer = Callable[[T], bytes]
Deserializer = Callable[[bytes], T]


class AsyncTaskCache(Generic[T]):
    """
    A generic cache for results of slow asynchronous tasks using Redis.
    Handles concurrent requests for the same key
    to avoid redundant computations.
    """

    def __init__(self, redis: Redis):
        self.redis = redis
        self.running_tasks: dict[str, asyncio.Task[T]] = {}

    async def get_or_create_task(
        self,
        key: str,
        task_func: Callable[[], Coroutine[Any, Any, T]],
        serializer: Serializer[T],
        deserializer: Deserializer[T],
        ttl: Optional[int] = None,
    ) -> T:
        """
        Retrieves a result from the cache or executes
        the task function if not cached.

        Handles race conditions where multiple requests for
        the same uncached key arrive concurrently, ensuring
        the task function is executed only once.

        :param key: The unique key for caching the task result.
        :param task_func: An asynchronous function (coroutine)
            that computes the result.
        :param serializer: A function to serialize the result (T) to bytes.
        :param deserializer: A function to deserialize bytes back
            to the result (T).
        :param ttl: Time-to-live for the cache entry in seconds.
            Uses settings.async_task_cache_ttl if None.
        :return: The result of the task function (T).
        :raises: Exception if the task_func raises an exception.
        """
        cache_ttl = ttl if ttl is not None else settings.async_task_cache_ttl

        try:
            cached_data = await self.redis.get(key)
            if cached_data:
                logger.debug(f'Cache hit for key: {key}')
                try:
                    return deserializer(cached_data)
                except Exception as e:
                    logger.warning(
                        f'Failed to deserialize cached data '
                        f'for key {key}: {e}. Treating as cache miss.'
                    )
        except ConnectionError:
            logger.warning(
                'Redis connection error during GET. Proceeding without cache.'
            )
        except Exception as e:
            logger.error(
                f'Unexpected error during cache GET '
                f'for key {key}: {e}. Proceeding without cache.'
            )

        logger.debug(f'Cache miss for key: {key}')

        if key in self.running_tasks:
            logger.debug(
                f'Task already running for key: {key}. Awaiting existing task.'
            )
            try:
                return await self.running_tasks[key]
            except Exception as e:
                logger.error(f'Awaited running task for key {key} failed: {e}')
                raise

        logger.debug(f'Starting new task for key: {key}')
        task = asyncio.create_task(
            self._run_and_cache_task(key, task_func, serializer, cache_ttl)
        )
        self.running_tasks[key] = task

        try:
            result = await task
            return result
        except Exception as e:
            logger.error(f'Newly created task for key {key} failed: {e}')
            raise
        finally:
            if key in self.running_tasks and self.running_tasks[key] is task:
                logger.debug(
                    f'Removing completed/failed task '
                    f'from running_tasks for key: {key}'
                )
                del self.running_tasks[key]

    async def _run_and_cache_task(
        self,
        key: str,
        task_func: Callable[[], Coroutine[Any, Any, T]],
        serializer: Serializer[T],
        ttl: int,
    ) -> T:
        """
        Internal helper: Runs the task, serializes, caches,
        and returns the result.
        This function is executed within an asyncio.Task.
        """
        try:
            result: T = await task_func()
            logger.debug(
                f'Task function completed successfully for key: {key}'
            )

            try:
                serialized_data = serializer(result)
            except Exception as e:
                logger.error(
                    f'Failed to serialize result for key {key}: {e}. '
                    f'Result will not be cached.'
                )
                return result

            try:
                await self.redis.set(
                    key,
                    serialized_data,
                    ex=ttl,
                )
                logger.debug(
                    f'Successfully cached result for key: '
                    f'{key} with TTL {ttl}s'
                )
            except ConnectionError:
                logger.warning(
                    f'Redis connection error during SET for key {key}. '
                    f'Result not cached.'
                )
            except Exception as e:
                logger.error(
                    f'Failed to set cache for key {key}: {e}. '
                    f'Result not cached.'
                )
            return result

        except Exception as e:
            logger.error(
                f'Exception occurred within the task_func '
                f'for key {key}: {e}'
            )
            raise

    def clear(self):
        self.running_tasks.clear()


async_task_cache: AsyncTaskCache = AsyncTaskCache(
    Redis.from_url(settings.redis_url)
)
