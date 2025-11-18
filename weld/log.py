import os
import sys
import tempfile

from loguru import logger


def setup_logger():
    # pick a writable log path
    log_dir = os.path.join(tempfile.gettempdir(), "weld")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "weld.log")

    # Log to console (stdout)
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        enqueue=True,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green>"
        + " | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>"
        + ":<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Log to file (in /tmp/weld/weld.log)
    logger.add(
        log_path,
        rotation="1 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD at HH:mm:ss}"
        + " | {level} | {name}:{function}:{line} - {message}",
    )


def log_info(msg: str):
    logger.opt(depth=1).info(msg)


def log_debug(msg: str):
    logger.opt(depth=1).debug(msg)


def log_warning(msg: str):
    logger.opt(depth=1).warning(msg)


def log_error(msg: str):
    logger.opt(depth=1).error(msg)


def log_exception(msg: str):
    logger.opt(depth=1).exception(msg)


__all__ = [
    "log_info",
    "log_debug",
    "log_warning",
    "log_error",
    "log_exception",
    "setup_logger",
]
