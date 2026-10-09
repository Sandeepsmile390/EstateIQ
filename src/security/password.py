"""
Pure Argon2id Password Hashing Engine (src/security/password.py).
Provides strict, secure one-way password hashing using Argon2id (OWASP recommended parameters).
Legacy/alternative password hashing algorithms (PBKDF2) have been completely removed.

Algorithm Parameters:
- Type: Argon2id (Side-channel & GPU attack resistant)
- Time Cost (t): 2 iterations
- Memory Cost (m): 19456 KiB (~19 MB)
- Parallelism (p): 1 thread
- Salt Length: 16 bytes cryptographically secure random salt
"""

import logging
from typing import Tuple, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

logger = logging.getLogger("EstateIQ.Security.Password")


class PasswordService:
    """
    Strict Argon2id Password Service providing one-way password hashing and verification.
    """

    def __init__(self):
        # OWASP recommended Argon2id parameters
        self._ph = PasswordHasher(
            time_cost=2,
            memory_cost=19456,
            parallelism=1,
            hash_len=32,
            salt_len=16
        )

    def hash_password(self, password: str) -> str:
        """
        Hashes password using Argon2id with a fresh random salt.

        Args:
            password: Plaintext password

        Returns:
            Argon2id encoded hash string (e.g. '$argon2id$v=19$m=19456,t=2,p=1$...')
        """
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string.")
        return self._ph.hash(password)

    def verify_password(self, password: str, stored_hash: str) -> Tuple[bool, bool]:
        """
        Verifies plaintext password strictly against Argon2id hash format.

        Args:
            password: Plaintext password attempt
            stored_hash: Stored Argon2id hash string

        Returns:
            Tuple[is_valid: bool, needs_rehash: bool]
        """
        if not password or not stored_hash:
            return False, False

        if not (stored_hash.startswith("$argon2id$") or stored_hash.startswith("$argon2i$")):
            logger.warning("Rejected non-Argon2id password hash format.")
            return False, False

        try:
            is_valid = self._ph.verify(stored_hash, password)
            needs_rehash = self._ph.check_needs_rehash(stored_hash)
            return is_valid, needs_rehash
        except VerifyMismatchError:
            return False, False
        except InvalidHashError:
            logger.warning("Invalid Argon2 hash format encountered.")
            return False, False


# Singleton instance
_DEFAULT_PASSWORD_SERVICE = PasswordService()

def get_password_service() -> PasswordService:
    return _DEFAULT_PASSWORD_SERVICE

def hash_password(password: str) -> str:
    return get_password_service().hash_password(password)

def verify_password(password: str, stored_hash: str) -> Tuple[bool, bool]:
    return get_password_service().verify_password(password, stored_hash)
