import base64
import hashlib
import logging
import os
from cryptography.fernet import Fernet

_logger = logging.getLogger(__name__)


_KEY_FIELDS: tuple[str, ...] = (
    "api_key",
    "anthropic_api_key",
    "openrouter_api_key",
    "adzuna_app_key",
    "linkedin_api_key",
    "indeed_api_key",
    "glassdoor_api_key",
)


def _get_fernet() -> Fernet:
    raw = os.getenv("SECRET_KEY", "ai-career-studio-dev-secret-2026")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


def _is_encrypted(value) -> bool:
    """True only if value is already a Fernet v1 ciphertext (starts with 'gAAAAA')."""
    return bool(value) and isinstance(value, str) and value.startswith("gAAAAA")


def encrypt_key(val) -> str:
    """Encrypt a plain-text key. Returns val unchanged if empty or already encrypted."""
    if not val or _is_encrypted(val):
        return val
    return _get_fernet().encrypt(val.encode()).decode()


def decrypt_key(val) -> str:
    """Decrypt a Fernet ciphertext. Returns val unchanged if empty or not encrypted."""
    if not val or not _is_encrypted(val):
        return val
    try:
        return _get_fernet().decrypt(val.encode()).decode()
    except Exception:
        _logger.warning("Failed to decrypt value; returning as-is (wrong key or corrupted ciphertext)")
        return val
