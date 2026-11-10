"""MATRIX Structured Logging Configuration.
Provides colored console output with Rich and persistent rotating file logging.
"""
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from config.settings import settings


def setup_logging() -> logging.Logger:
    """Initialize structured logging handlers for MATRIX."""
    log_level = logging.DEBUG if settings.debug else logging.INFO
    log_dir = Path(settings.logs_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "matrix.log"

    # Configure root logger
    logger = logging.getLogger("matrix")
    logger.setLevel(log_level)

    # Avoid duplicate handlers on re-initialization
    if not logger.handlers:
        # Rich console handler with custom formatting
        console_handler = RichHandler(
            level=log_level,
            show_time=True,
            show_level=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True
        )
        console_formatter = logging.Formatter(
            fmt="[cyan]%(name)s[/cyan] - %(message)s",
            datefmt="[%X]"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Persistent rotating file handler (max 10MB per file, 5 backups)
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Suppress verbose noise from external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Retrieve a child logger under the MATRIX namespace."""
    return logging.getLogger(f"matrix.{name}")


# Global logger instance
logger = setup_logging()
