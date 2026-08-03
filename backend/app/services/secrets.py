"""Secrets management service with masking and rotation support."""

import base64
import hashlib
import hmac
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import get_settings

settings = get_settings()


class SecretsManager:
    """Manages secrets with encryption, masking, and rotation support."""

    def __init__(self):
        self._encryption_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        self._rotation_period_days = int(os.getenv("SECRET_ROTATION_PERIOD_DAYS", "90"))
        self._rotation_buffer_days = int(os.getenv("SECRET_ROTATION_BUFFER_DAYS", "7"))

    @property
    def encryption_key(self) -> bytes:
        """Get or derive the encryption key."""
        if self._encryption_key is None:
            raw_key = os.getenv("ENCRYPTION_KEY", "")
            if not raw_key:
                # Generate a key for development
                self._encryption_key = secrets.token_bytes(32)
            else:
                # Use PBKDF2 to derive a key from the environment variable
                salt = b"nebula-salt-2024"
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100_000,
                )
                self._encryption_key = kdf.derive(raw_key.encode())

            # Create Fernet instance
            self._fernet = Fernet(self._encryption_key)

        return self._encryption_key

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not data:
            return data
        encrypted = self._fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not encrypted_data:
            return encrypted_data
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except InvalidToken:
            raise ValueError("Invalid encrypted data or encryption key mismatch")

    def mask(self, data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data for logging, keeping only last N chars visible."""
        if not data or len(data) <= visible_chars:
            return "*" * len(data) if data else ""
        return "*" * (len(data) - visible_chars) + data[-visible_chars:]

    def mask_dict(self, data: dict, mask_keys: list[str]) -> dict:
        """Mask sensitive fields in a dictionary."""
        result = data.copy()
        for key in mask_keys:
            if key in result and result[key]:
                result[key] = self.mask(str(result[key]))
        return result

    def needs_rotation(self, created_at: datetime) -> bool:
        """Check if a secret needs rotation based on rotation period."""
        now = datetime.now(timezone.utc)
        age_days = (now - created_at).days
        return age_days > (self._rotation_period_days - self._rotation_buffer_days)

    def generate_secure_string(
        self, length: int = 32, include_upper: bool = True, include_lower: bool = True,
        include_digits: bool = True, include_symbols: bool = True
    ) -> str:
        """Generate a cryptographically secure random string."""
        charset = ""
        if include_upper:
            charset += string.ascii_uppercase
        if include_lower:
            charset += string.ascii_lowercase
        if include_digits:
            charset += string.digits
        if include_symbols:
            charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Ensure at least one character from each selected category
        result = []
        if include_upper:
            result.append(secrets.choice(string.ascii_uppercase))
        if include_lower:
            result.append(secrets.choice(string.ascii_lowercase))
        if include_digits:
            result.append(secrets.choice(string.digits))
        if include_symbols:
            result.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))

        # Fill remaining length with random characters
        while len(result) < length:
            result.append(secrets.choice(charset))

        # Shuffle the result
        result_list = list(result)
        secrets.SystemRandom().shuffle(result_list)

        return "".join(result_list)

    def generate_jti(self) -> str:
        """Generate a unique JWT ID for token invalidation."""
        return secrets.token_urlsafe(32)

    def verify_secret_hash(self, secret: str, hash_value: str, salt: str) -> bool:
        """Verify a secret against its hash (for backup codes, etc.)."""
        # Combine secret with salt and hash
        combined = secret + salt
        hash_obj = hashlib.sha256(combined.encode())
        return hmac.compare_digest(hash_obj.hexdigest(), hash_value)


# Global instance
secrets_manager = SecretsManager()


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Convenience function to mask sensitive data."""
    return secrets_manager.mask(data, visible_chars)


def mask_dict_fields(data: dict, mask_keys: list[str]) -> dict:
    """Convenience function to mask sensitive fields in a dict."""
    return secrets_manager.mask_dict(data, mask_keys)
