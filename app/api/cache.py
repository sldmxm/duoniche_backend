import logging
import time
from asyncio import Lock
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class ValidationCache:
    def __init__(self, max_size=100, cache_timeout=300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, Lock] = {}
        self._max_size = max_size
        self._cache_timeout = cache_timeout

    async def get_or_create_validation(
        self, key: str, validation_func: Callable
    ):
        if key not in self._locks:
            self._locks[key] = Lock()

        async with self._locks[key]:
            cache_entry = self._cache.get(key)

            if (
                cache_entry
                and time.time() - cache_entry.get('timestamp', 0)
                < self._cache_timeout
            ):
                return cache_entry['result']

            result = await validation_func()

            self._cache[key] = {'result': result, 'timestamp': time.time()}

            if len(self._cache) > self._max_size:
                oldest_key = min(
                    self._cache, key=lambda k: self._cache[k]['timestamp']
                )
                del self._cache[oldest_key]

            return result


validation_cache = ValidationCache()
