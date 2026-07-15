"""Logging setup for the trading bot.

Configures structured logging with color output for terminal and file rotation.
"""

import logging
import sys
from pathlib import Path

import colorlog


def setup_logging(config) -> logging.Logger:
    """Setup logging configuration.

    Args:
        config: Configuration object with logging settings

    Returns:
        Logger instance configured with console and file handlers
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Get log level from config
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    # Create main logger
    logger = logging.getLogger("bybit_trader")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Color format for console
    color_format = (
        "%(log_color)s%(asctime)s | %(levelname)-8s | "
        "%(name)s | %(message)s%(reset)s"
    )

    console_formatter = colorlog.ColoredFormatter(
        color_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler if enabled
    if config.logging.save_to_file:
        _setup_file_handlers(logger, log_dir, log_level)

    return logger


def _setup_file_handlers(logger: logging.Logger, log_dir: Path, log_level: int) -> None:
    """Setup file handlers for logging.

    Args:
        logger: Logger instance to add handlers to
        log_dir: Directory for log files
        log_level: Logging level
    """
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Main log file
    file_handler = logging.FileHandler(log_dir / "trading.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Error log file
    error_handler = logging.FileHandler(log_dir / "errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)

    # Scanner log file
    scanner_handler = logging.FileHandler(log_dir / "scanner.log")
    scanner_handler.setLevel(logging.INFO)
    scanner_handler.setFormatter(file_formatter)
    logger.addHandler(scanner_handler)

    # API log file
    api_handler = logging.FileHandler(log_dir / "api.log")
    api_handler.setLevel(logging.DEBUG)
    api_handler.setFormatter(file_formatter)
    logger.addHandler(api_handler)
