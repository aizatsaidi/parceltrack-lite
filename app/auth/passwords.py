"""Password hashing helpers for Module 1 (Argon2id)."""
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return a salted Argon2id hash of ``password``."""
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Check a password, returning False for mismatches or invalid hashes."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False
