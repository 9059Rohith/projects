"""
Structured logging configuration for the Binance Futures Trading Bot.

Sets up rotating file handler (DEBUG) and stream handler (INFO).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Absolute path to the logs directory (relative to this file's project root)
_LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE = os.path.join(_LOGS_DIR, "trading_bot.log")

_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Maximum log file size before rotation (5 MB)
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

# Track whether the root logger has already been configured
_configured = False


def _configure_root_logger() -> None:
    """
    Configure the root logger with a rotating file handler and a stream handler.

    This function is idempotent — it will only configure the handlers once
    regardless of how many times it is called.
    """
    global _configured
    if _configured:
        return

    # Ensure the logs directory exists
    os.makedirs(_LOGS_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ------------------------------------------------------------------
    # Rotating File Handler — DEBUG level
    # ------------------------------------------------------------------
    file_handler = RotatingFileHandler(
        filename=_LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # ------------------------------------------------------------------
    # Stream Handler (stdout) — INFO level
    # ------------------------------------------------------------------
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Root must be DEBUG so file handler receives everything
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger. Configures the root logger on first call.

    Args:
        name: The logger name (typically the class or module name).

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)
