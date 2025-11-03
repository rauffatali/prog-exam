import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommendation for 2024
    )
    # Derive key and encode as Fernet key (base64url)
    key_material = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key_material)