"""Logging utilities for the trading bot."""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Optional

from config.settings import Settings


def configure_logging(settings: Settings, level: int = logging.INFO) -> None:
    """Configure structured logging for the application."""

    log_dir: Path = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                },
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": str(log_dir / "bot.log"),
                    "when": "midnight",
                    "backupCount": 7,
                    "formatter": "default",
                    "level": level,
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": level,
            },
        }
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger."""

    return logging.getLogger(name if name else __name__)


__all__ = ["configure_logging", "get_logger"]
