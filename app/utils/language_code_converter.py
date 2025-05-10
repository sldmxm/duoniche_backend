import logging

import pycountry

logger = logging.getLogger(__name__)


def convert_iso639_language_code_to_full_name(language_code: str) -> str:
    language = language_code
    try:
        lang_obj = pycountry.languages.get(alpha_2=language_code.lower())
        if lang_obj and hasattr(lang_obj, 'name'):
            language = lang_obj.name
        elif lang_obj and hasattr(lang_obj, 'common_name'):
            language = lang_obj.common_name
    except Exception as e:
        logger.warning(
            f'Could not find full name for language code '
            f"'{language_code}': {e}. Using the code itself."
        )
    return language


if __name__ == '__main__':
    languages_map = {
        'uk': 'Ukrainian',
        'en': 'English',
        'bg': 'Bulgarian',
        'ru': 'Russian',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
    }
    for code, full in languages_map.items():
        print(convert_iso639_language_code_to_full_name(code) == full)
