from html.parser import HTMLParser

ALLOWED_TAGS = {'b', 'i', 'u', 'code', 's'}
TAG_REPLACEMENTS = {
    'br': '\n',
    'p': '\n',
    'div': '\n',
    'li': '\n- ',
    'ul': '\n',
    'ol': '\n',
    'span': '',
}


class CustomHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_starttag(self, tag, attrs):
        if tag in ALLOWED_TAGS:
            self.result.append(f'<{tag}>')
        elif tag in TAG_REPLACEMENTS:
            self.result.append(TAG_REPLACEMENTS[tag])

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS:
            self.result.append(f'</{tag}>')

    def handle_data(self, data):
        self.result.append(data)


def clean_html_for_telegram(text: str) -> str:
    parser = CustomHTMLParser()
    parser.feed(text)
    return ''.join(parser.result)
