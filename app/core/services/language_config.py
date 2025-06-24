import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # type: ignore

from app.core.enums import ExerciseType
from app.core.generation.config import ExerciseTopic

logger = logging.getLogger(__name__)


class LanguageConfigService:
    _instance: Optional['LanguageConfigService'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LanguageConfigService, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = (
            Path(__file__).parent.parent / 'configs' / 'language_config.yml'
        )
        if not config_path.exists():
            logger.error(
                f'Language configuration file not found at: {config_path}'
            )
            raise FileNotFoundError(
                f'Language configuration file not found at: {config_path}'
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        logger.info(
            f'Language configuration loaded for languages: '
            f'{list(self._config.keys())}'
        )

    def get_config(self, bot_id: str) -> Optional[Dict[str, Any]]:
        return self._config.get(bot_id)

    def get_all_bot_ids(self) -> List[str]:
        return list(self._config.keys())

    def get_language_code(self, bot_id: str) -> Optional[str]:
        config = self.get_config(bot_id)
        return config.get('language_code') if config else None

    def get_topics_excluded_from_generation(
        self, bot_id: str
    ) -> Optional[List[ExerciseTopic]]:
        config = self.get_config(bot_id)
        if not config:
            return None

        str_topics_exclude_from_generation = config.get(
            'topics_exclude_from_generation'
        )
        if not str_topics_exclude_from_generation:
            return None

        topics_exclude_from_generation = [
            ExerciseTopic(t) for t in str_topics_exclude_from_generation
        ]

        return topics_exclude_from_generation

    def get_exercise_types_excluded_from_generation(
        self, bot_id: str
    ) -> Optional[List[ExerciseType]]:
        config = self.get_config(bot_id)
        if not config:
            return None

        str_exercise_types_exclude_from_generation = config.get(
            'exercise_types_exclude_from_generation'
        )
        if not str_exercise_types_exclude_from_generation:
            return None

        exercise_types_exclude_from_generation = [
            ExerciseType(t) for t in str_exercise_types_exclude_from_generation
        ]
        return exercise_types_exclude_from_generation
