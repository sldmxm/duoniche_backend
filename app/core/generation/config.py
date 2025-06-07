import random
from enum import Enum
from typing import Dict, List, Optional

from app.core.generation.persona import Persona


class ExerciseTopic(Enum):
    GENERAL = 'general'
    SHOPPING = 'shopping'
    TRAVEL = 'travel'
    FOOD = 'food'
    SPORTS = 'sports'
    WEATHER = 'weather'
    WORK = 'work'
    HEALTH = 'health'
    EMERGENCIES = 'emergencies'
    RELATIONSHIPS = 'relationships'
    TECH = 'tech'
    EDUCATION = 'education'
    ENTERTAINMENT = 'entertainment'
    MONEY = 'money'
    HOME = 'home'
    TRANSPORT = 'transport'
    RESTAURANT = 'restaurant'
    FAMILY = 'family'
    PHARMACY = 'pharmacy'
    NATURE = 'NATURE'
    ANIMALS = 'ANIMALS'
    KIDS = 'KIDS'
    HOUSING = 'housing'
    CULTURE = 'culture'
    DATING = 'dating'
    WINE = 'wine'
    DIGITAL_LIFE = 'digital_life'
    PUBLIC_SERVICES = 'public_services'

    @classmethod
    def get_next_topic(cls) -> 'ExerciseTopic':
        topics: List[ExerciseTopic] = list(ExerciseTopic)
        return random.choice(topics)

    @classmethod
    def get_topic_for_generation(
        cls,
        exclude_topics: Optional[List['ExerciseTopic']] = None,
        topic_weights: Optional[Dict['ExerciseTopic', float]] = None,
    ) -> 'ExerciseTopic':
        """
        Returns a topic for exercise generation,
        allowing for exclusions and weighting.

        :param exclude_topics: A list of topics to exclude from selection.
        :param topic_weights: A dictionary mapping topics to their
                                selection weights.
                              If None, all available topics are chosen with
                                equal probability.
                              Topics not in this dict (but not excluded) will
                                have a default weight of 1.0.
        :return: A selected ExerciseTopic.
        """
        available_topics = list(cls)
        if exclude_topics:
            available_topics = [
                topic
                for topic in available_topics
                if topic not in exclude_topics
            ]

        if not available_topics:
            return cls.GENERAL

        if topic_weights:
            weights = []
            valid_topics_for_weighting = []
            for topic in available_topics:
                valid_topics_for_weighting.append(topic)
                weights.append(topic_weights.get(topic, 1.0))

            if not valid_topics_for_weighting or all(w <= 0 for w in weights):
                return random.choice(available_topics)

            return random.choices(
                valid_topics_for_weighting, weights=weights, k=1
            )[0]
        else:
            return random.choice(available_topics)


TOPIC_GROUPS = {
    'SERVICE': {
        ExerciseTopic.SHOPPING,
        ExerciseTopic.RESTAURANT,
        ExerciseTopic.PHARMACY,
        ExerciseTopic.PUBLIC_SERVICES,
    },
    'DAILY_LIFE': {
        ExerciseTopic.HOME,
        ExerciseTopic.HOUSING,
        ExerciseTopic.TRANSPORT,
        ExerciseTopic.MONEY,
        ExerciseTopic.FAMILY,
        ExerciseTopic.KIDS,
    },
    'SOCIAL': {
        ExerciseTopic.WORK,
        ExerciseTopic.EDUCATION,
        ExerciseTopic.RELATIONSHIPS,
        ExerciseTopic.DATING,
        ExerciseTopic.CULTURE,
    },
    'LEISURE': {
        ExerciseTopic.TRAVEL,
        ExerciseTopic.ENTERTAINMENT,
        ExerciseTopic.WINE,
        ExerciseTopic.NATURE,
        ExerciseTopic.ANIMALS,
        ExerciseTopic.SPORTS,
    },
    'HEALTH_EMERGENCY': {ExerciseTopic.HEALTH, ExerciseTopic.EMERGENCIES},
    'NEUTRAL': {
        ExerciseTopic.GENERAL,
        ExerciseTopic.FOOD,
        ExerciseTopic.WEATHER,
        ExerciseTopic.DIGITAL_LIFE,
        ExerciseTopic.TECH,
    },
}

PERSONAS: dict[str, Persona] = {
    'Embarrassed Tourist': Persona(
        name='Embarrassed Tourist',
        role='tourist',
        emotion='embarrassed',
        motivation='is looking for help, afraid of looking stupid',
        emotion_instruction_for_tts='Say hesitantly and a little shyly:',
    ),
    'Irritated Customer': Persona(
        name='Irritated Customer',
        role='customer',
        emotion='irritated',
        motivation='believes they are being deceived',
        emotion_instruction_for_tts='Say with irritation:',
    ),
    'Friendly Barista': Persona(
        name='Friendly Barista',
        role='barista',
        communication_style='friendly, talkative',
        emotion_instruction_for_tts='Say cheerfully and friendly:',
    ),
    'Suspicious Pensioner': Persona(
        name='Suspicious Pensioner',
        role='pensioner',
        emotion='suspicious',
        communication_style='distrustful',
        emotion_instruction_for_tts='Say suspiciously:',
    ),
    'Rushing Student': Persona(
        name='Rushing Student',
        role='student',
        motivation='in a big hurry',
        emotion_instruction_for_tts='Say a little bit quickly and a bit '
        'breathlessly:',
    ),
    'Apathetic Taxi Driver': Persona(
        name='Apathetic Taxi Driver',
        role='taxi driver',
        emotion='apathy, tired of life',
        communication_style='laconic',
        emotion_instruction_for_tts='Say apathetically and monotonously:',
    ),
    'Demanding Client': Persona(
        name='Demanding Client',
        role='client',
        communication_style='demanding, laconic',
        emotion_instruction_for_tts='Say demandingly and clearly:',
    ),
    'Ironic Colleague': Persona(
        name='Ironic Colleague',
        role='colleague',
        communication_style='ironic, sarcastic',
        emotion_instruction_for_tts='Say with irony:',
    ),
    'Polite Waiter': Persona(
        name='Polite Waiter',
        role='waiter',
        communication_style='extremely polite',
        motivation='wants to get good tips',
        emotion_instruction_for_tts='Say very politely and courteously:',
    ),
    # 'Tired Cashier': Persona(
    #     name='Tired Cashier',
    #     role='cashier',
    #     emotion='tired',
    #     motivation='wants to finish the shift quickly',
    #     emotion_instruction_for_tts='Say wearily:',
    # ),
}

PERSONA_TOPICS: dict[str, set[str]] = {
    # 'Tired Cashier': {'SERVICE', 'DAILY_LIFE'},
    'Embarrassed Tourist': {'LEISURE', 'HEALTH_EMERGENCY', 'SERVICE'},
    'Irritated Customer': {'SERVICE', 'NEUTRAL', 'DAILY_LIFE'},
    'Friendly Barista': {'SERVICE', 'NEUTRAL', 'LEISURE'},
    'Suspicious Pensioner': {
        'DAILY_LIFE',
        'SERVICE',
        'HEALTH_EMERGENCY',
    },
    'Rushing Student': {'SOCIAL', 'DAILY_LIFE'},
    'Apathetic Taxi Driver': {'DAILY_LIFE', 'LEISURE'},
    'Demanding Client': {'SERVICE', 'NEUTRAL', 'SOCIAL'},
    'Ironic Colleague': {'SOCIAL', 'NEUTRAL'},
    'Polite Waiter': {'SERVICE', 'LEISURE'},
}
