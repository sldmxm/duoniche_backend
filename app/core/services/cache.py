import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from app.config import settings
from app.core.entities.exercise_answer import ExerciseAnswer

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    is_correct: bool
    feedback: str
    answer_id: Optional[int] = None


class ValidationCache:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.running_tasks: dict[str, asyncio.Task] = {}

    async def get_or_create_validation(
        self,
        key: str,
        validation_func: Callable[[], Coroutine[Any, Any, ExerciseAnswer]],
    ) -> ExerciseAnswer:
        """
        Get a validation result from the cache or create a new one.

        :param key: Cache key
        :param validation_func: Function to call
                                if the result is not in the cache
        :return: Validation result
        """
        try:
            cached_result = await self.redis.get(key)
            if cached_result:
                logger.debug(f'Cache hit for key: {key}')
                return ExerciseAnswer.model_validate_json(cached_result)
        except ConnectionError:
            logger.warning('Redis connection error')

        logger.debug(f'Cache miss for key: {key}')

        if key in self.running_tasks:
            logger.debug(f'Task already running for key: {key}')
            task = self.running_tasks[key]
            return await task

        logger.debug(f'Starting new task for key: {key}')
        task = asyncio.create_task(
            self._run_and_cache_validation(key, validation_func)
        )
        self.running_tasks[key] = task
        return await task

    async def _run_and_cache_validation(
        self,
        key: str,
        validation_func: Callable[[], Coroutine[Any, Any, ExerciseAnswer]],
    ) -> ExerciseAnswer:
        """
        Run the validation function, cache the result,
        and remove the task from running_tasks.
        """
        try:
            validation_result = await validation_func()
            try:
                await self.redis.set(
                    key,
                    validation_result.model_dump_json(),
                    ex=settings.cache_ttl,
                )
            except ConnectionError:
                logger.warning('Redis connection error')
            return validation_result
        finally:
            del self.running_tasks[key]


validation_cache = ValidationCache(Redis.from_url(settings.redis_url))
