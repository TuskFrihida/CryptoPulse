"""
Logging configuration.

Real automation runs unattended, so good logging is how you find out what
happened while you were asleep. We log to BOTH the console (for when you watch
it live) and a rotating file in logs/ (for history). Rotation keeps the log
files from growing forever.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import LOGS_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger, setting up handlers only once."""
    logger = logging.getLogger(name)

    # If this logger was already configured, don't add duplicate handlers.
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT)

    # Console handler — what you see in the terminal.
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler — keeps up to 3 files of 1 MB each.
    file_handler = RotatingFileHandler(
        LOGS_DIR / "cryptopulse.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
