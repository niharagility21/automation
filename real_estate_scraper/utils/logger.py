"""
Logging configuration for the real estate scraper.

Provides structured logging with timestamps, severity levels, and
both console and file output for debugging and monitoring.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from config.settings import LOG_LEVEL, LOG_FILE


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.

    Args:
        name: Logger name (usually __name__ of calling module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, defaults to settings.LOG_FILE)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Scraper started")
        >>> logger.error("Failed to fetch page", exc_info=True)
    """
    # Create logger
    logger = logging.getLogger(name)

    # Set level from parameter or settings
    log_level = getattr(logging, (level or LOG_LEVEL).upper(), logging.DEBUG)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = ColoredFormatter(
        fmt='%(levelname)s | %(asctime)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (plain text, no colors)
    file_path = log_file or LOG_FILE
    file_handler = logging.FileHandler(file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        fmt='%(levelname)s | %(asctime)s | %(name)s | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def log_retry_attempt(
    logger: logging.Logger,
    url: str,
    attempt: int,
    max_retries: int,
    delay: int,
    reason: Optional[str] = None
) -> None:
    """
    Log a retry attempt with formatted details.

    Args:
        logger: Logger instance
        url: URL being retried
        attempt: Current attempt number (1-indexed)
        max_retries: Maximum number of retries
        delay: Delay in seconds before next attempt
        reason: Optional reason for retry (e.g., "timeout", "403 forbidden")
    """
    reason_str = f" (Reason: {reason})" if reason else ""
    logger.warning(
        f"Retry {attempt}/{max_retries} for {url}{reason_str}. "
        f"Waiting {delay}s before next attempt..."
    )


def log_proxy_rotation(
    logger: logging.Logger,
    old_proxy: Optional[str],
    new_proxy: str,
    reason: str = "scheduled rotation"
) -> None:
    """
    Log proxy rotation event.

    Args:
        logger: Logger instance
        old_proxy: Previous proxy (None if first proxy)
        new_proxy: New proxy being used
        reason: Reason for rotation (e.g., "failed", "scheduled rotation")
    """
    old_display = old_proxy if old_proxy else "None"
    # Hide credentials in logs (show only host:port)
    new_display = new_proxy.split('@')[-1] if '@' in new_proxy else new_proxy

    logger.info(
        f"Proxy rotation ({reason}): {old_display} -> {new_display}"
    )


def log_extraction_success(
    logger: logging.Logger,
    scraper_name: str,
    records_count: int,
    duration_seconds: float
) -> None:
    """
    Log successful data extraction.

    Args:
        logger: Logger instance
        scraper_name: Name of scraper that completed
        records_count: Number of records extracted
        duration_seconds: Time taken in seconds
    """
    logger.info(
        f"✓ {scraper_name} completed successfully: "
        f"{records_count} records extracted in {duration_seconds:.2f}s"
    )


def log_extraction_error(
    logger: logging.Logger,
    scraper_name: str,
    error: Exception,
    url: Optional[str] = None
) -> None:
    """
    Log extraction error with details.

    Args:
        logger: Logger instance
        scraper_name: Name of scraper that failed
        error: Exception that occurred
        url: Optional URL where error occurred
    """
    url_str = f" at {url}" if url else ""
    logger.error(
        f"✗ {scraper_name} failed{url_str}: {type(error).__name__}: {str(error)}",
        exc_info=True
    )


# Create default logger for module-level use
default_logger = setup_logger("real_estate_scraper")
