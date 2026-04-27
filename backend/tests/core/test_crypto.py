from app.core.crypto import decrypt_secret, encrypt_secret


def test_encrypt_and_decrypt_roundtrip() -> None:
    original = "my-app-password-123"
    encrypted = encrypt_secret(original)
    assert encrypted != original
    assert decrypt_secret(encrypted) == original
