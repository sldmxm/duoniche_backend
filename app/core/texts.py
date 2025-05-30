import random
from enum import Enum
from typing import Any, Dict, List, Union, cast

from app.config import settings
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
            '💪You’re crushing it! On to the next one!\n'
            'Want to change the interface language? Current is 🇬🇧, '
            'but you can switch to 🇧🇬🇷🇺🇹🇷🇺🇦 via /my_language',
        ],
        'bg': [
            '🎉Справяте се чудесно! Продължавайте!',
            '👏Страхотен напредък! Не спирайте!',
            '💪Перфектна работа! Напред към следващото!\n'
            'Искаш ли да смениш езика на интерфейса? В момента е 🇧🇬, '
            'но можеш да избереш друг: 🇬🇧🇷🇺🇹🇷🇺🇦 — с /my_language',
        ],
        'tr': [
            '🎉Harika gidiyorsunuz! Devam edin!',
            '👏Süper ilerleme! Aynen böyle devam!',
            '💪Müthişsiniz! Hadi sıradaki!\n'
            'Arayüz dili şu anda 🇹🇷, ama 🇧🇬🇬🇧🇷🇺🇺🇦 dillerinden '
            'birini /my_language ile seçebilirsin',
        ],
        'ru': [
            '🎉Вы отлично справляетесь! Так держать!',
            '👏Отличный прогресс! Продолжайте в том же духе!',
            '💪Вы молодец! Вперёд к следующему!\n'
            'Хочешь изменить язык интерфейса? Сейчас выбран 🇷🇺, '
            'но можно выбрать другой: 🇧🇬🇬🇧🇹🇷🇺🇦 — через /my_language',
        ],
        'uk': [
            '🎉Ви чудово справляєтесь! Продовжуйте!',
            '👏Супер прогрес! Не зупиняйтесь!',
            '💪Молодці! Рухаймось далі!\n'
            'Хочеш змінити мову інтерфейсу? Зараз вибрано 🇺🇦, '
            'але можна обрати іншу: 🇧🇬🇬🇧🇷🇺🇹🇷 — через /my_language',
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
        'uk': '🥳Круто! Виконано вже {exercise_num} вправ!\n'
        '🕑Час на коротку перерву — досягнуто ліміту на зараз. '
        'Наступна вправа буде доступна через {pause_time}. 💪',
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
    ExerciseType.STORY_COMPREHENSION: {
        'ru': 'Послушай текст и выбери верное утверждение',
        'en': 'Listen to the text and choose the correct statement',
        'bg': 'Чуй текста и избери вярното твърдение',
        'tr': 'Metni dinle ve doğru ifadeyi seç',
        'uk': 'Прослухай текст і вибери правильне твердження',
    },
}


class Reminder(str, Enum):
    SESSION_IS_READY = 'session_is_ready'
    LONG_BREAK_1D_STREAK = 'long_break_1d_streak'
    LONG_BREAK_1D = 'long_break_1d'
    LONG_BREAK_3D = 'long_break_3d'
    LONG_BREAK_5D = 'long_break_5d'
    LONG_BREAK_8D = 'long_break_8d'
    LONG_BREAK_13D = 'long_break_13d'
    LONG_BREAK_21D = 'long_break_21d'
    LONG_BREAK_30D = 'long_break_30d'
    LONG_BREAK_FINAL = 'long_break_final'


DEFAULT_LONG_BREAK_REMINDER = Reminder.LONG_BREAK_5D

REMINDERS_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    Reminder.SESSION_IS_READY: {
        'en': '🚀Ready to level up? Your new session is here '
        '— time to sharpen your skills!',
        'bg': '🚀Готови ли сте да напреднете? Новата ви сесия е тук '
        '— време е да подобрите уменията си!',
        'tr': '🚀Hazır mısınız? Yeni oturum geldi '
        '— becerilerinizi geliştirme zamanı!',
        'ru': '🚀Готовы прокачаться? Новая сессия уже доступна '
        '— время тренироваться!',
        'uk': '🚀Готові підкорювати нові вершини? Нова сесія чекає на вас '
        '— вперед до знань!',
    },
    Reminder.LONG_BREAK_1D_STREAK: {
        'en': "🔥You're on a {streak_days}-day streak "
        "— that's impressive! Don't break the rhythm now!",
        'bg': '🔥Серията ти вече е {streak_days} 📆 '
        '— впечатляващо! Не прекъсвай ритъма!',
        'ru': '🔥У тебя уже серия {streak_days} 📆 '
        '— крутой результат! Не сбивай ритм!',
        'tr': '🔥Serin şu anda {streak_days} 📆 gün! '
        'Harika, bırakma şimdi!',
        'uk': '🔥У тебе вже серія {streak_days} 📆 '
        '— це круто! Не зупиняйся!',
    },
    Reminder.LONG_BREAK_1D: {
        'en': '📚Time to practice a bit — around this time yesterday, '
        "you were crushing it! Let's keep it going!",
        'bg': '📚Време е за малко практика — по това време вчера се '
        'справяше страхотно! Продължавай в същия дух!',
        'ru': '📚Пора немного позаниматься — вчера ты в это время '
        'был молодцом и прокачивал язык! Держим темп!',
        'tr': '📚Hadi biraz pratik yapalım — dün tam bu '
        'saatte harikaydın! Aynı tempoda devam!',
        'uk': '📚Час трохи попрактикуватися — у цей час учора '
        'ти був на хвилі! Тримай темп!',
    },
    Reminder.LONG_BREAK_3D: {
        'en': '⌛It’s been 3 days without practice. '
        "One quick session — and you're back in the game!",
        'bg': '⌛Изминаха 3 дни без практика. '
        'Една бърза сесия и си обратно в играта!',
        'ru': '⌛Прошло 3 дня без практики. '
        'Одна быстрая сессия — и ты снова в игре!',
        'tr': '⌛3 gündür pratik yok. ' 'Kısa bir seansla yeniden oyundasın!',
        'uk': '⌛Минуло 3 дні без практики. '
        'Швидка сесія — і ти знову в грі!',
    },
    Reminder.LONG_BREAK_5D: {
        'en': '🌱The best time to plant a tree was 20 years ago. '
        'The second best is now. Same with language learning.',
        'bg': '🌱Най-доброто време да посадиш дърво беше преди 20 години. '
        'Второто най-добро е сега. С езика е същото.',
        'ru': '🌱Лучшее время посадить дерево было 20 лет назад. '
        'Второе лучшее — сейчас. С языком то же самое.',
        'tr': '🌱Bir ağacı dikmek için en iyi zaman 20 yıl önceydi. '
        'İkincisi ise şimdi. Dil öğrenmek de böyle.',
        'uk': '🌱Найкращий час посадити дерево був 20 років тому. '
        'Другий найкращий — зараз. Із мовами так само.',
    },
    Reminder.LONG_BREAK_8D: {
        'en': '🌟Every step counts — even after 8 days. '
        'Your progress is waiting for you!',
        'bg': '🌟Всяка крачка има значение — дори след 8 дни. '
        'Напредъкът ти те очаква!',
        'ru': '🌟Каждый шаг важен — даже спустя 8 дней. '
        'Твой прогресс ждёт тебя!',
        'tr': '🌟Her adım önemli — 8 gün sonra bile. '
        'Gelişimin seni bekliyor!',
        'uk': '🌟Кожен крок має значення — навіть після 8 днів. '
        'Твій прогрес чекає на тебе!',
    },
    Reminder.LONG_BREAK_13D: {
        'en': '⏳13 days away? No worries. The journey is still waiting. '
        'Ready to take the next step?',
        'bg': '⏳13 дни без практика? Няма страшно. Пътят те чака. '
        'Готов ли си за следващата стъпка?',
        'ru': '⏳13 дней без практики? Не беда. Путь всё ещё ждёт тебя. '
        'Готов сделать следующий шаг?',
        'tr': '⏳13 gündür ara mı verdin? '
        'Sorun değil. Yolculuk seni bekliyor. '
        'Bir adım daha atmaya var mısın?',
        'uk': '⏳13 днів без практики? Не біда. Твоя подорож чекає. '
        'Готовий зробити наступний крок?',
    },
    Reminder.LONG_BREAK_21D: {
        'en': '⌛We know time is tight and language isn’t the top priority '
        '— but even a few minutes can keep you moving forward.',
        'bg': '⌛Знаем, че времето не стига и езикът не е на първо място '
        '— но и няколко минути са важни за напредък.',
        'ru': '⌛Понимаем — времени ни на что не хватает, язык '
        '— не на первом месте. Но даже пара минут помогут '
        'не остановиться.',
        'tr': '⌛Zamanın dar olduğunu ve dilin öncelikli olmadığını '
        'biliyoruz — ama birkaç dakika bile ilerlemeni sağlar.',
        'uk': '⌛Розуміємо — часу бракує і мова не на першому місці. '
        'Але навіть кілька хвилин допоможуть не зупинитись.',
    },
    Reminder.LONG_BREAK_30D: {
        'en': '🥹 It’s been exactly a month since your last session. '
        'No pressure, but maybe now’s a great time to continue?',
        'bg': '🥹 Измина точно месец от последното ти занимание. '
        'Без натиск, но може би сега е чудесен момент да продължиш?',
        'ru': '🥹 Прошёл ровно месяц с твоего последнего занятия. '
        'Ни на что не намекаю, но, кажется, отличный момент'
        ' продолжить.',
        'tr': '🥹 Son oturumundan tam bir ay geçti. Baskı yapmıyorum '
        'ama belki şimdi devam etmek için harika bir zaman?',
        'uk': '🥹 Минув рівно місяць з твого останнього заняття. Без '
        'тиску, але, здається, чудовий момент продовжити.',
    },
    Reminder.LONG_BREAK_FINAL: {
        'en': '🤗 It’s been a while since your last session. '
        'No more reminders — I’ll miss you quietly...',
        'bg': '🤗 Измина доста време от последното ти занимание. '
        'Никакви напомняния повече — ще ми липсваш тихо...',
        'ru': '🤗 Прошло уже немало времени с твоего последнего занятия. '
        'Никаких напоминаний больше — буду скучать молча...',
        'tr': '🤗 Son oturumundan bu yana epey zaman geçti. '
        'Artık hatırlatma yok — sessizce özleyeceğim...',
        'uk': '🤗 Минуло вже чимало часу з твого останнього заняття. '
        'Жодних нагадувань більше — мовчки сумуватиму...',
    },
}


class PaymentMessages(str, Enum):
    BUTTON_TEXT = 'payment_button_text'
    TITLE = 'payment_title'
    DESCRIPTION = 'payment_description'
    ITEM_LABEL = 'payment_item_label'
    THANKS_ANSWER = 'payment_thanks_answer'
    ITEM_LABEL_TIER_1 = 'payment_item_label_tier_1'
    ITEM_LABEL_TIER_2 = 'payment_item_label_tier_2'
    ITEM_LABEL_TIER_3 = 'payment_item_label_tier_3'
    ITEM_LABEL_TIER_4 = 'payment_item_label_tier_4'
    ITEM_LABEL_TIER_5 = 'payment_item_label_tier_5'
    ITEM_LABEL_TIER_6 = 'payment_item_label_tier_6'


PAYMENT_TRANSLATIONS: Dict[PaymentMessages, Dict[str, str]] = {
    PaymentMessages.BUTTON_TEXT: {
        'ru': '☕️ Поддержать и продолжить сейчас',
        'en': '☕️ Support and continue now',
        'bg': '☕️ Подкрепи и продължи сега',
        'tr': '☕️ Destekle ve hemen devam et',
        'uk': '☕️ Підтримати і продовжити зараз',
    },
    PaymentMessages.TITLE: {
        'ru': '☕️ Поддержать',
        'en': '☕️ Support',
        'bg': '☕️ Подкрепа',
        'tr': '☕️ Destek',
        'uk': '☕️ Підтримка',
    },
    PaymentMessages.DESCRIPTION: {
        'ru': 'Поддержите проект — и еще одна сессия '
        'упражнений откроется сразу',
        'en': 'Support the project — and the next '
        'session will open immediately',
        'bg': 'Подкрепете проекта — и следващата '
        'сесия ще се отключи веднага',
        'tr': 'Projeyi destekle — bir sonraki ' 'oturum hemen açılacak',
        'uk': 'Підтримайте проєкт — і наступна ' 'сесія відкриється одразу',
    },
    PaymentMessages.ITEM_LABEL: {
        'ru': 'Открыть одну сессию',
        'en': 'Open one session',
        'bg': 'Отвори една сесия',
        'tr': 'Bir oturum aç',
        'uk': 'Відкрити одну сесію',
    },
    PaymentMessages.THANKS_ANSWER: {
        'en': 'Thank you for your support! ❤️',
        'bg': 'Благодаря за подкрепата! ❤️',
        'ru': 'Спасибо за поддержку! ❤️',
        'tr': 'Desteğiniz için teşekkürler! ❤️',
        'uk': 'Дякуємо за підтримку! ❤️',
    },
    PaymentMessages.ITEM_LABEL_TIER_1: {
        'ru': '💧 Капля поддержки',
        'en': '💧 A drop of support',
        'bg': '💧 Капка подкрепа',
        'tr': '💧 Bir damla destek',
        'uk': '💧 Крапля підтримки',
    },
    PaymentMessages.ITEM_LABEL_TIER_2: {
        'ru': '☕ Чашка кофе',
        'en': '☕ A cup of coffee',
        'bg': '☕ Чаша кафе',
        'tr': '☕ Bir fincan kahve',
        'uk': '☕ Чашка кави',
    },
    PaymentMessages.ITEM_LABEL_TIER_3: {
        'ru': '🏃‍♂️ Двигаемся дальше',
        'en': '🏃‍♂️ Keep it going',
        'bg': '🏃‍♂️ Продължаваме напред',
        'tr': '🏃‍♂️ Devam edelim',
        'uk': '🏃‍♂️ Рухаємось далі',
    },
    PaymentMessages.ITEM_LABEL_TIER_4: {
        'ru': '💡 Верю в идею',
        'en': '💡 Believe in the idea',
        'bg': '💡 Вярвам в идеята',
        'tr': '💡 Fikre inanıyorum',
        'uk': '💡 Вірю в ідею',
    },
    PaymentMessages.ITEM_LABEL_TIER_5: {
        'ru': '🚀 В развитие проекта',
        'en': '🚀 Help with growth',
        'bg': '🚀 За развитието на проекта',
        'tr': '🚀 Projeye katkı',
        'uk': '🚀 У розвиток проєкту',
    },
    PaymentMessages.ITEM_LABEL_TIER_6: {
        'ru': '👑 Легендарная поддержка',
        'en': '👑 Legendary support',
        'bg': '👑 Легендарна подкрепа',
        'tr': '👑 Efsanevi destek',
        'uk': '👑 Легендарна підтримка',
    },
}


def get_text(
    key: Union[Messages, ExerciseType, Reminder, PaymentMessages],
    language_code: str,
    **kwargs,
) -> str:
    if not isinstance(
        key, Messages | ExerciseType | Reminder | PaymentMessages
    ):
        raise ValueError(f'Unknown key type: {type(key)}')

    dictionary: Dict[Any, Dict[str, Union[str, List[str]]]]

    if isinstance(key, Messages):
        dictionary = cast(
            Dict[Any, Dict[str, Union[str, List[str]]]], MESSAGES_TRANSLATIONS
        )
    elif isinstance(key, ExerciseType):
        dictionary = cast(
            Dict[Any, Dict[str, Union[str, List[str]]]],
            EXERCISES_TASKS_TRANSLATIONS,
        )
    elif isinstance(key, Reminder):
        dictionary = cast(
            Dict[Any, Dict[str, Union[str, List[str]]]], REMINDERS_TRANSLATIONS
        )
    elif isinstance(key, PaymentMessages):
        dictionary = cast(
            Dict[Any, Dict[str, Union[str, List[str]]]], PAYMENT_TRANSLATIONS
        )
    else:
        raise ValueError(
            f'Unhandled key type for dictionary selection: {type(key)}'
        )

    if key not in dictionary:
        raise ValueError(f'Unknown key for translation: {key}')

    translations = dictionary[key]
    text_options = translations.get(language_code) or translations.get(
        settings.default_bot_message_language
    )

    if text_options is None:
        raise ValueError(
            f'No translation found for key '
            f"'{key.value if isinstance(key, Enum) else key}' "
            f"in language '{language_code}' "
            f"or default '{settings.default_bot_message_language}'."
        )

    if isinstance(text_options, list):
        text = random.choice(text_options)
    elif isinstance(text_options, str):
        text = text_options
    else:
        raise ValueError(
            f'Invalid translation format for key '
            f"'{key.value if isinstance(key, Enum) else key}'. "
            f'Expected str or list, got {type(text_options)}.'
        )

    if isinstance(key, Reminder):
        text += '\n\n/next'

    return text.format(**kwargs) if kwargs else text
