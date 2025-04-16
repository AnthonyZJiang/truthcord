import logging
import os
import dotenv
import requests
import uuid

ASHLEY_ID = 1313007325224898580
ANGELA_ID = 1313008328229785640
TESTER_ID = 185020620310839296

dotenv.load_dotenv()

AZURE_TRANSLATOR_KEY = os.getenv('AZURE_TRANSLATOR_KEY')
AZURE_TRANSLATOR_LOCATION = os.getenv('AZURE_TRANSLATOR_LOCATION')
TRANSLATE_FROM_LANGUAGE = os.getenv('TRANSLATE_FROM_LANGUAGE')
TRANSLATE_TO_LANGUAGE = os.getenv('TRANSLATE_TO_LANGUAGE')

class _ColourFormatter(logging.Formatter):

    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output

def setup_logging(level: str) -> None:
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = level_map.get(level.upper(), logging.INFO)

    handler = logging.StreamHandler()
    formatter = _ColourFormatter()
    
    library, _, _ = __name__.partition('.')
    logger = logging.getLogger(library)

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)

def azure_translate(payload: list[dict[str, str]], from_language: str=TRANSLATE_FROM_LANGUAGE, to_language: str=TRANSLATE_TO_LANGUAGE) -> dict[str, str]:
    if not AZURE_TRANSLATOR_KEY or not AZURE_TRANSLATOR_LOCATION:
        return {
            'error': 'Azure Translator API details missing.'
        }
    api_url = 'https://api.cognitive.microsofttranslator.com/translate'

    params = {
        'api-version': '3.0',
        'from': from_language,
        'to': to_language
    }

    headers = {
        'Ocp-Apim-Subscription-Key': AZURE_TRANSLATOR_KEY,
        'Ocp-Apim-Subscription-Region': AZURE_TRANSLATOR_LOCATION,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    request = requests.post(api_url, params=params, headers=headers, json=payload)
    response = request.json()

    if not response:
        return {
            'error': 'No response from Azure Translator'
        }
    if isinstance(response, dict):
        if response.get('error', None):
            return {
                'error': f'{response["error"]["code"]}: {response["error"]["message"]}'
            }
    if isinstance(response, list):
        return {
            'translations': [r['translations'][-1]['text'] for r in response]
        }
    return {
        'translations': [response['translations'][-1]['text']]
    }
