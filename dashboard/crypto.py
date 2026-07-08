"""
Encrypts/decrypts account credentials at rest using Fernet (AES-128-CBC +
HMAC), keyed from the DASHBOARD_SECRET_KEY env var. Without this key, the
SQLite file alone reveals nothing usable.

Generate a key once with:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64
import hashlib
import json
import os

from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.getenv("DASHBOARD_SECRET_KEY", "")
    if not key:
        raise RuntimeError(
            "DASHBOARD_SECRET_KEY is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n'
            "and set it as an environment variable before starting the dashboard.")
    # Accept either a proper Fernet key or an arbitrary passphrase (hashed to 32 bytes)
    try:
        return Fernet(key.encode())
    except Exception:
        digest = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_dict(data: dict) -> str:
    """Serialize a credentials dict to an encrypted string for DB storage."""
    plaintext = json.dumps(data).encode()
    return _get_fernet().encrypt(plaintext).decode()


def decrypt_dict(token: str) -> dict:
    """Reverse of encrypt_dict. Raises ValueError on tampered/wrong-key data."""
    try:
        plaintext = _get_fernet().decrypt(token.encode())
    except InvalidToken:
        raise ValueError("Could not decrypt credentials — wrong DASHBOARD_SECRET_KEY "
                         "or corrupted data.")
    return json.loads(plaintext)
