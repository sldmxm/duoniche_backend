from datetime import timedelta

from app.core.enums import LanguageLevel

EXERCISE_FILL_IN_THE_BLANK_BLANKS = '___'

DEFAULT_LANGUAGE_LEVEL = LanguageLevel.A2
DEFAULT_USER_LANGUAGE = 'ru'
DEFAULT_TARGET_LANGUAGE = 'Bulgarian'

DEFAULT_BOT_MESSAGE_LANGUAGE = 'bg'
EXERCISES_IN_SET = 5
SETS_IN_SESSION = 3
EXERCISES_IN_SESSION = EXERCISES_IN_SET * SETS_IN_SESSION
DELTA_BETWEEN_SESSIONS = timedelta(hours=3)
RENEWING_SET_PERIOD = timedelta(
    seconds=int(DELTA_BETWEEN_SESSIONS.total_seconds() // SETS_IN_SESSION)
)
MAX_SESSIONS_LENGTH = timedelta(hours=3)

# there is no point longer, it will already be in the db
# and no new ones will be started.
ASYNC_TASK_CACHE_TTL: int = 60 * 2
