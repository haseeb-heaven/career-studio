"""Tests for Fernet key encryption helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from crypto import _is_encrypted, encrypt_key, decrypt_key


def test_is_encrypted_false_for_plain_text():
    assert _is_encrypted("sk-abc123") is False


def test_is_encrypted_false_for_empty_string():
    assert _is_encrypted("") is False


def test_is_encrypted_false_for_none():
    assert _is_encrypted(None) is False


def test_is_encrypted_true_for_fernet_prefix():
    assert _is_encrypted("gAAAAAbunchofbase64==") is True


def test_encrypt_key_produces_fernet_token():
    ct = encrypt_key("my-secret-key")
    assert ct.startswith("gAAAAA")


def test_decrypt_key_round_trip():
    plain = "sk-test-12345"
    ct = encrypt_key(plain)
    assert decrypt_key(ct) == plain


def test_encrypt_key_idempotent_already_encrypted():
    ct = encrypt_key("original")
    ct2 = encrypt_key(ct)  # must not double-encrypt
    assert ct2 == ct
    assert decrypt_key(ct2) == "original"


def test_encrypt_key_empty_passthrough():
    assert encrypt_key("") == ""


def test_decrypt_key_plain_passthrough():
    assert decrypt_key("plain-text") == "plain-text"


def test_decrypt_key_empty_passthrough():
    assert decrypt_key("") == ""
