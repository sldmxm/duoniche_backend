import logging
import sys

from app.config import settings


def configure_logging() -> None:
    """
    Configures the root logger for the application.
    """
    debug = settings.debug.lower() == 'true'
    log_level = logging.DEBUG if debug else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s '
            '- %(name)s '
            '- %(levelname)s '
            '- %(module)s '
            '- %(funcName)s '
            '- %(message)s'
        )
        console_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)


# configure_logging()
