# utils/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

try:
    from config import BASE_DIR
    DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "logs")
except ImportError:
    DEFAULT_LOG_DIR = os.path.join(os.path.expanduser("~"), ".airebar", "logs")


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int):
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def setup_logger(
    name: str,
    log_dir: str = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
):
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    safe_name = name.replace(".", "_")
    log_file = os.path.join(log_dir, f"{safe_name}.log")

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(file_level)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(min(console_level, logging.INFO))
    stdout_handler.addFilter(_MaxLevelFilter(logging.INFO))

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(max(logging.WARNING, console_level))

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for h in (file_handler, stdout_handler, stderr_handler):
        h.setFormatter(formatter)
        logger.addHandler(h)

    return logger


def get_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(name)
    if not lg.handlers:
        lg = setup_logger(name)
    return lg