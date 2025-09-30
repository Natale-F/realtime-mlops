import logging
import os

import structlog
from dotenv import load_dotenv

load_dotenv()


def setup_logging(level: int | None = logging.INFO) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: The logging level to use. Defaults to INFO.
    """
    # Basic configuration
    logging.basicConfig(level=level)

    # Configure processors for structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
            pad_event=50,  # For better alignment of logs
        ),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


if os.getenv("LOG_LEVEL") == "INFO":
    setup_logging(level=logging.INFO)
elif os.getenv("LOG_LEVEL") == "DEBUG":
    setup_logging(level=logging.DEBUG)
elif os.getenv("LOG_LEVEL") == "WARNING":
    setup_logging(level=logging.WARNING)
elif os.getenv("LOG_LEVEL") == "ERROR":
    setup_logging(level=logging.ERROR)
elif os.getenv("LOG_LEVEL") == "CRITICAL":
    setup_logging(level=logging.CRITICAL)
else:
    setup_logging(level=logging.DEBUG)

log = structlog.get_logger("General logger")
