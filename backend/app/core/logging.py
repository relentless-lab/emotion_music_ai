import logging
from typing import Optional

from app.core.config import settings


def configure_logging(level: Optional[int] = None) -> None:
    """Configure application level logging."""
    log_level = level if level is not None else logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

