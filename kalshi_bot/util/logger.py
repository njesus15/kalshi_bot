# kalshi_bot/util/logger.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str = "kalshi_bot") -> logging.Logger:
    """
    Returns a beautifully formatted logger with:
      • Colored console output
      • Daily rotating log files (max 5MB × 7 backups)
      • Precise timestamps
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():  # Prevent duplicate handlers in reloads/notebooks
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)  # Capture everything

    # ── Console Handler (pretty colors) ─────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    console_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    # Add colors with colorlog (optional but awesome)
    try:
        import colorlog
        color_format = colorlog.ColoredFormatter(
            fmt="%(log_color)s%(asctime)s | %(levelname)8s | %(name)12s | %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(color_format)
    except ImportError:
        console_handler.setFormatter(console_format)

    logger.addHandler(console_handler)

    # ── File Handler (rotating logs) ───────────────────────────────────────
    file_handler = RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=5_000_000,    # 5 MB
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    file_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger