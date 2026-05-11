import logging
import os

from logging import Logger
from pathlib import Path

"""
===============================================================================

	Logger

===============================================================================
"""

PROJECT_DIR = Path(__file__).resolve().parents[2]
_LOG_DIR: Path = PROJECT_DIR / "logs"


def get_logger(name: str, *, log_dir: Path = _LOG_DIR, console: bool = False) -> Logger:
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"{name}.log"

    log_path = os.path.join(log_dir, log_filename)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    file_handler = logging.FileHandler(log_path, mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # suppress paralel logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger
