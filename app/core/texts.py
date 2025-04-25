from enum import Enum
from typing import Dict, cast

from app.core.consts import DEFAULT_BOT_MESSAGE_LANGUAGE
from app.core.enums import ExerciseType


class Messages(str, Enum):
    ERROR_GETTING_NEW_EXERCISE = 'error_getting_new_exercise'
    CONGRATULATIONS_AND_WAIT = 'congratulations'
    LIMIT_REACHED = 'limit_reached'
    PRAISE_AND_NEXT_SET = 'praise_and_next_set'


MESSAGES_TRANSLATIONS: Dict[Messages, Dict[str, str]] = {
    Messages.ERROR_GETTING_NEW_EXERCISE: {
        'en': "🥺Sorry, I couldn't get a new exercise " 'for you right now.',
        'bg': '🥺Съжалявам, но в момента не мога да ви '
        'предложа ново упражнение.',
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
    Messages.CONGRATULATIONS_AND_WAIT: {
        'en': "🥳Wow! You've completed "
        '{exercise_num} exercises!\n'
        '🕑You have reached the limit for moment. '
        "Please wait a moment, I'll send the next "
        'exercise as soon as I get a chance.',
        'bg': '🥳Браво! Изпълнихте {exercise_num} упражнения!\n'
        '🕑Достигнахте лимита за момента. Моля, изчакайте малко, ще '
        'изпратя следващото упражнение веднага'
        ' щом ми се отдаде възможност.',
        'tr': '🥳Vay canına! {exercise_num} egzersizlerini tamamladınız!\n'
        '🕑Şu an için sınıra ulaştınız.'
        'Lütfen biraz bekleyin, fırsat bulur bulmaz '
        'bir sonraki alıştırmayı göndereceğim.',
    },
}

EXERCISES_TASKS_TRANSLATIONS: Dict[ExerciseType, Dict[str, str]] = {
    ExerciseType.FILL_IN_THE_BLANK: {
        'ru': 'Заполни пробелы в предложении',
        'en': 'Fill in the blanks in the sentence',
        'bg': 'Попълнете празните места в изречението',
        'tr': 'Cümledeki boşlukları doldurun',
        'uk': 'Заповніть пропуски у реченні',
    },
    ExerciseType.CHOOSE_SENTENCE: {
        'ru': 'Выбери корректное предложение',
        'en': 'Choose the correct sentence',
        'bg': 'Изберете правилното изречение',
        'tr': 'Doğru cümleyi seçin',
        'uk': 'Виберіть правильне речення',
    },
    ExerciseType.CHOOSE_ACCENT: {
        'ru': 'Выбери правильное ударение',
        'en': 'Choose the correct accent',
        'bg': 'Изберете правилния акцент',
        'tr': 'Doğru aksanı seçin',
        'uk': 'Виберіть правильний акцент',
    },
}


def get_text(
    key: Messages | ExerciseType, language_code: str, **kwargs
) -> str:
    if not isinstance(key, Messages | ExerciseType):
        raise ValueError(f'Unknown key type: {type(key)}')

    dictionary = cast(
        Dict[Messages | ExerciseType, Dict[str, str]],
        MESSAGES_TRANSLATIONS
        if isinstance(key, Messages)
        else EXERCISES_TASKS_TRANSLATIONS,
    )

    if key not in dictionary:
        raise ValueError(f'Unknown key for translation: {key}')

    translations = dictionary[key]
    if language_code in translations:
        text = translations[language_code]
    else:
        text = translations[DEFAULT_BOT_MESSAGE_LANGUAGE]

    return text.format(**kwargs) if kwargs else text
