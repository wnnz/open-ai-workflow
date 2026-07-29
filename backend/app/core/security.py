import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet

from app.core.config import get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, get_settings().app_secret_key, algorithms=["HS256"])
    return str(payload["sub"])


def create_app_access_token(
    workflow_id: str, grant_id: str, expires_at: datetime | None = None
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    token_expires_at = now + timedelta(hours=12)
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        token_expires_at = min(token_expires_at, expires_at)
    payload = {
        "sub": workflow_id,
        "grant_id": grant_id,
        "kind": "app_access",
        "iat": now,
        "exp": token_expires_at,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_app_access_token(token: str) -> tuple[str, str]:
    payload = jwt.decode(token, get_settings().app_secret_key, algorithms=["HS256"])
    if payload.get("kind") != "app_access":
        raise ValueError("Invalid app access token")
    return str(payload["sub"]), str(payload["grant_id"])


def invitation_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def api_key_token() -> tuple[str, str, str]:
    raw = f"owf_{secrets.token_urlsafe(32)}"
    return raw, raw[:12], token_hash(raw)


def _fernet() -> Fernet:
    settings = get_settings()
    if settings.credential_encryption_key:
        configured = settings.credential_encryption_key.encode()
        try:
            return Fernet(configured)
        except ValueError:
            if settings.app_env.casefold() == "production":
                raise RuntimeError(
                    "CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key in production"
                ) from None
            key = base64.urlsafe_b64encode(hashlib.sha256(configured).digest())
    else:
        digest = hashlib.sha256(settings.app_secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
