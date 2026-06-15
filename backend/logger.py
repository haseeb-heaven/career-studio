"""Centralised logging — stdout (INFO) + rotating file in project logs/ folder (DEBUG)."""
import io
import logging
import logging.handlers
import sys
from pathlib import Path

# Write logs to career-studio/logs/ (one level above backend/)
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "career_studio.log"

_ROOT = "career_studio"
_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    logger = logging.getLogger(f"{_ROOT}.{name}")

    if not _configured:
        _configured = True

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Rotating file — 5 MB × 3 backups, DEBUG level
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)

        # Stdout — INFO level, UTF-8 so Unicode chars (→ etc.) don't crash on Windows cp1252
        try:
            _stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        except AttributeError:
            _stream = sys.stdout  # fallback if stdout has no buffer (e.g. redirected)
        sh = logging.StreamHandler(_stream)
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)

        root = logging.getLogger(_ROOT)
        root.setLevel(logging.DEBUG)
        if not root.handlers:
            root.addHandler(fh)
            root.addHandler(sh)

    return logger
