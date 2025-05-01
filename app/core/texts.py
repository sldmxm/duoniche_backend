import random
from enum import Enum
from typing import Dict, List, Union, cast

from app.core.consts import DEFAULT_BOT_MESSAGE_LANGUAGE
from app.core.enums import ExerciseType


class Messages(str, Enum):
    ERROR_GETTING_NEW_EXERCISE = 'error_getting_new_exercise'
    CONGRATULATIONS_AND_WAIT = 'congratulations'
    LIMIT_REACHED = 'limit_reached'
    PRAISE_AND_NEXT_SET = 'praise_and_next_set'


MESSAGES_TRANSLATIONS: Dict[Messages, Dict[str, Union[str, List[str]]]] = {
    Messages.ERROR_GETTING_NEW_EXERCISE: {
        'en': "🥺Sorry, I couldn't get a new exercise for you right now.",
        'bg': '🥺Съжалявам, но в момента не мога да ви '
        'предложа ново упражнение.',
    },
    Messages.LIMIT_REACHED: {
        'en': '🥺Sorry, you have reached the limit for moment. Please, wait. '
        'The next exercise will be available in {pause_time}',
        'bg': '🥺Съжалявам, достигнали сте лимита за момента. '
        'Следващото упражнение ще бъде достъпно след {pause_time}',
        'ru': '🥺Извините, на данный момент вы исчерпали свой лимит. '
        'Следующее упражнение будет доступно через {pause_time}',
        'tr': '🥺Üzgünüm, limitinize ulaştınız. '
        'Bir sonraki egzersiz {pause_time}’te hazır olacak.',
    },
    # TODO: Разные сообщения для разного количества ошибок
    #  найти за что хвалить, например,
    #  за короткое или длинное время сета
    Messages.PRAISE_AND_NEXT_SET: {
        'en': [
            '🎉You are doing great! Keep going!',
            '👏Awesome progress! Let’s keep the streak alive!',
            '💪You’re crushing it! On to the next one!',
        ],
        'bg': [
            '🎉Справяте се чудесно! Продължавайте!',
            '👏Страхотен напредък! Не спирайте!',
            '💪Перфектна работа! Напред към следващото!',
        ],
        'tr': [
            '🎉Harika gidiyorsunuz! Devam edin!',
            '👏Süper ilerleme! Aynen böyle devam!',
            '💪Müthişsiniz! Hadi sıradaki!',
        ],
        'ru': [
            '🎉Вы отлично справляетесь! Так держать!',
            '👏Отличный прогресс! Продолжайте в том же духе!',
            '💪Вы молодец! Вперёд к следующему!',
        ],
        'uk': [
            '🎉Ви чудово справляєтесь! Продовжуйте!',
            '👏Супер прогрес! Не зупиняйтесь!',
            '💪Молодці! Рухаймось далі!',
        ],
    },
    Messages.CONGRATULATIONS_AND_WAIT: {
        'en': '🥳Awesome! You’ve nailed {exercise_num} exercises!\n'
        "🕑Time for a quick break — you've hit your limit for now. "
        'The next one will be ready in {pause_time}. 💪',
        'bg': '🥳Браво! Справихте се с {exercise_num} упражнения!\n'
        '🕑Време е за кратка почивка — достигнахте лимита за сега. '
        'Следващото упражнение ще бъде готово след {pause_time}. 💪',
        'tr': '🥳Harika! {exercise_num} alıştırmayı başarıyla tamamladınız!\n'
        '🕑Kısa bir mola zamanı — şimdilik limitinize ulaştınız. '
        'Yeni alıştırma {pause_time} içinde hazır olacak! 💪',
        'ru': '🥳Супер! Вы справились с {exercise_num} упражнениями!\n'
        '🕑Пора на короткий перерыв — вы достигли лимита. '
        'Новое упражнение будет готово через {pause_time}. 💪',
    },
}

EXERCISES_TASKS_TRANSLATIONS: Dict[
    ExerciseType, Dict[str, Union[str, List[str]]]
] = {
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
        Dict[Messages | ExerciseType, Dict[str, Union[str, List[str]]]],
        MESSAGES_TRANSLATIONS
        if isinstance(key, Messages)
        else EXERCISES_TASKS_TRANSLATIONS,
    )

    if key not in dictionary:
        raise ValueError(f'Unknown key for translation: {key}')

    translations = dictionary[key]
    text_options = translations.get(language_code) or translations.get(
        DEFAULT_BOT_MESSAGE_LANGUAGE
    )

    if isinstance(text_options, list):
        text = random.choice(text_options)
    elif isinstance(text_options, str):
        text = text_options
    else:
        raise ValueError('Invalid translation format')

    return text.format(**kwargs) if kwargs else text
