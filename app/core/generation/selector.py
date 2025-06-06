import random
from typing import Optional

from app.core.generation.config import (
    PERSONA_TOPICS,
    PERSONAS,
    TOPIC_GROUPS,
    ExerciseTopic,
)
from app.core.generation.persona import Persona

TOPIC_TO_GROUP_MAP = {
    topic: group for group, topics in TOPIC_GROUPS.items() for topic in topics
}


def select_persona_for_topic(topic: ExerciseTopic) -> Optional[Persona]:
    """
    Selects a random, compatible persona for a given exercise topic.
    """
    topic_group = TOPIC_TO_GROUP_MAP.get(topic)
    if not topic_group:
        return None

    compatible_persona_names = [
        name
        for name, groups in PERSONA_TOPICS.items()
        if topic_group in groups
    ]

    if not compatible_persona_names:
        return None

    selected_name = random.choice(compatible_persona_names)

    return PERSONAS.get(selected_name)
