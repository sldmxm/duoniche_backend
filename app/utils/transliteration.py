import re
from typing import Callable, Optional

import cyrtranslit


def to_cyrillic(text: Optional[str]) -> str:
    """Transliterates a string from Latin to Serbian Cyrillic."""
    if not text:
        return ''
    return cyrtranslit.to_cyrillic(text, 'sr')


def to_latin(text: Optional[str]) -> str:
    """Transliterates a string from Cyrillic to Serbian Latin."""
    if not text:
        return ''
    return cyrtranslit.to_latin(text, 'sr')


def transliterate_code_blocks(
    text: str, transliterator: Callable[[str], str]
) -> str:
    """
    Finds all substrings within `<code>...</code>` tags and applies
    the transliterator function to their content. This is safer than
    transliterating based on general quotes.

    :param text: The input string containing mixed language text and code tags.
    :param transliterator: The function to apply (e.g., to_cyrillic).
    :return: The text with content inside <code> tags transliterated.
    """
    if not text:
        return ''

    pattern = re.compile(r'<code>(.*?)</code>')

    # Функция замены стала намного проще
    def replace_match(match: re.Match) -> str:
        return f'<code>{transliterator(match.group(1))}</code>'

    return pattern.sub(replace_match, text)
