from enum import Enum
from typing import Dict, Optional

from app.core.consts import DEFAULT_BOT_MESSAGE_LANGUAGE, EXERCISES_IN_SESSION


class Messages(str, Enum):
    ERROR_GETTING_NEW_EXERCISE = 'error_getting_new_exercise'
    CONGRATULATIONS_AND_WAIT = 'congratulations'
    LIMIT_REACHED = 'limit_reached'
    PRAISE_AND_NEXT_SET = 'praise_and_next_set'


TRANSLATIONS: Dict[Messages, Dict[str, str]] = {
    Messages.ERROR_GETTING_NEW_EXERCISE: {
        'en': "🥺Sorry, I couldn't get a new exercise " 'for you right now.',
        'bg': '🥺Съжалявам, но в момента не мога да ви '
        'предложа ново упражнение.',
    },
    # TODO:
    #  - Разные сообщения для разного количества ошибок
    #  найти за что хвалить, например,
    #   за короткое или длинное время сессии
    #  - Второе сообщение отдельно в боте
    #   "подожди или плоти", разделить \n
    Messages.CONGRATULATIONS_AND_WAIT: {
        'en': "🥳Wow! You've completed "
        f'{EXERCISES_IN_SESSION} exercises!\n'
        '🕑You have reached the limit for moment. '
        "Please wait a moment, I'll send the next "
        'exercise as soon as I get a chance.',
        'bg': f'🥳Браво! Изпълнили сте {EXERCISES_IN_SESSION} упражнения!\n'
        '🕑Достигнали сте лимита за момента. Моля, изчакайте малко, ще '
        'изпратя следващото упражнение веднага щом имам възможност.',
    },
    Messages.LIMIT_REACHED: {
        'en': '🥺Sorry, you have reached the limit for moment. Please, wait. '
        "I'll send you new exercise ASAP...",
        'bg': '🥺Съжалявам, достигнали сте лимита за момента. '
        'Ще ви изпратя нови упражнения възможно най-скоро...',
    },
    # TODO: Разные сообщения для разного количества ошибок
    #  найти за что хвалить, например,
    #  за короткое или длинное время сета
    Messages.PRAISE_AND_NEXT_SET: {
        'en': '🎉You are doing great! Keep going!',
        'bg': '🎉Справяте се чудесно! Продължавайте!',
    },
}


def get_text(key: Messages, language_code: str, **kwargs) -> Optional[str]:
    if key not in TRANSLATIONS:
        return None
    translations = TRANSLATIONS[key]
    if language_code in translations:
        text = translations[language_code]
    else:
        text = translations[DEFAULT_BOT_MESSAGE_LANGUAGE]

    return text.format(**kwargs) if kwargs else text
