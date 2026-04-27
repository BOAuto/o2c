import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _build_fernet() -> Fernet:
    secret_bytes = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(secret_bytes).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    fernet = _build_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    fernet = _build_fernet()
    try:
        decrypted = fernet.decrypt(value.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted secret payload") from exc
    return decrypted.decode("utf-8")
