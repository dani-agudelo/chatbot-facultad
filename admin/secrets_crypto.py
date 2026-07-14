"""Cifrado en reposo de secretos admin (Fernet derivado de JWT_SECRET)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from admin.settings import get_admin_settings


def _fernet() -> Fernet:
    secret = get_admin_settings().jwt_secret.encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    value = plaintext.strip()
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str | None) -> str:
    if not token or not token.strip():
        return ""
    try:
        return _fernet().decrypt(token.strip().encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""
