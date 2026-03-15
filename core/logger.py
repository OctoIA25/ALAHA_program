import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "alaha.log"

_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_formatter)
_file_handler.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
_console_handler.setLevel(logging.INFO)

_log_callbacks: list = []


class _CallbackHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        for cb in _log_callbacks:
            try:
                cb(msg)
            except Exception:
                pass


_callback_handler = _CallbackHandler()
_callback_handler.setFormatter(_formatter)
_callback_handler.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"alaha.{name}")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)
        logger.addHandler(_callback_handler)
    return logger


def register_log_callback(callback) -> None:
    _log_callbacks.append(callback)
