import logging
import sys

from app.config import settings


def configure_logging() -> None:
    """
    Configures the root logger for the application.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.parsed_log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.parsed_log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)


configure_logging()
