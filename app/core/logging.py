"""Logging configuration for local + container deployment.

Uvicorn's own access log covers request lines. This adds a consistent
formatter for app-level logs, and matters most for the unhandled-exception
path: core/exceptions.py's catch-all handler used to swallow every unexpected
error silently (a clean 500 JSON response went out, but nothing was ever
logged) -- invisible once the app runs on a remote box where `docker logs`
is the only window in.
"""

import logging
import sys

from app.core.config import settings

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers = [handler]

    # Quiet noisy third-party loggers below our own threshold unless asked.
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"atelier_lens.{name}")
