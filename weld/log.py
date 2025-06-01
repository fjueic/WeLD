import sys

from loguru import logger

# Log to console (stdout)
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green>"
    + " | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>"
    + ":<cyan>{line}</cyan> - <level>{message}</level>",
)

# Log to file with rotation and retention
logger.add(
    "weld.log",
    rotation="1 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD at HH:mm:ss}"
    + " | {level} | {name}:{function}:{line} - {message}",
)


def log_info(msg: str):
    logger.info(msg)


def log_debug(msg: str):
    logger.debug(msg)


def log_warning(msg: str):
    logger.warning(msg)


def log_error(msg: str):
    logger.error(msg)


def log_exception(msg: str):
    logger.exception(msg)


__all__ = [
    "log_info",
    "log_debug",
    "log_warning",
    "log_error",
    "log_exception",
]
