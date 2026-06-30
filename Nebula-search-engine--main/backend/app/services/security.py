"""Security utilities: password hashing, TOTP, WebAuthn, API keys, encryption."""

import base64
import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional, Tuple

from app.config import get_settings

logger = logging.getLogger("nebula.security")
settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing — bcrypt with PBKDF2 backward compatibility
# ---------------------------------------------------------------------------

_PBKDF2_PREFIX = "pbkdf2$"
_BCRYPT_PREFIX = "bcrypt$"


def hash_password_bcrypt(password: str) -> str:
    """Hash a password using bcrypt (preferred)."""
    import bcrypt as _bcrypt

    salt = _bcrypt.gensalt(rounds=12)
    hashed = _bcrypt.hashpw(password.encode("utf-8"), salt)
    return f"{_BCRYPT_PREFIX}{hashed.decode('ascii')}"


def verify_password_bcrypt(password: str, stored: str) -> bool:
    """Verify a bcrypt-hashed password."""
    import bcrypt as _bcrypt

    try:
        _, raw = stored.split("$", 1)
        return _bcrypt.checkpw(
            password.encode("utf-8"), raw.encode("ascii")
        )
    except Exception as exc:
        logger.warning("verify_password_bcrypt failed: %s", exc)
        return False


def hash_password(password: str) -> str:
    """Hash password with bcrypt.

    Backward-compatible: PBKDF2 hashes (without prefix) are still verified
    via :func:`verify_password`.
    """
    return hash_password_bcrypt(password)


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored hash (bcrypt or legacy PBKDF2)."""
    if not stored:
        return False

    # Legacy PBKDF2 (no prefix, format: salt$hex)
    if "$" in stored and not stored.startswith("pbkdf2$") and not stored.startswith("bcrypt$"):
        try:
            salt, hashed = stored.split("$", 1)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 200_000
            )
            return secrets.compare_digest(dk.hex(), hashed)
        except Exception as exc:
            logger.warning("Legacy PBKDF2 verification failed: %s", exc)
            return False

    # Prefixed PBKDF2
    if stored.startswith(_PBKDF2_PREFIX):
        try:
            _, rest = stored.split("$", 1)
            salt, hashed = rest.split("$", 1)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 200_000
            )
            return secrets.compare_digest(dk.hex(), hashed)
        except Exception as exc:
            logger.warning("Prefixed PBKDF2 verification failed: %s", exc)
            return False

    # bcrypt
    if stored.startswith(_BCRYPT_PREFIX):
        return verify_password_bcrypt(password, stored)

    return False


# ---------------------------------------------------------------------------
# TOTP (2FA)
# ---------------------------------------------------------------------------


def generate_totp_secret() -> str:
    """Generate a new TOTP secret key (base32 encoded)."""
    import pyotp

    return pyotp.random_base32()


def get_totp_provisioning_uri(email: str, secret: str) -> str:
    """Get the ``otpauth://`` URI for QR-code enrollment."""
    import pyotp

    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.totp_issuer)


def verify_totp(secret: str, token: str) -> bool:
    """Verify a TOTP token against the stored secret."""
    import pyotp

    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


# ---------------------------------------------------------------------------
# WebAuthn (basic)
# ---------------------------------------------------------------------------

_WEBAUTHN_RP_ID = settings.cors_origin_list[0] if settings.cors_origin_list else "localhost"
_WEBAUTHN_RP_NAME = "Nebula Search"
_WEBAUTHN_ORIGIN = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:3000"


def generate_webauthn_registration_options(
    email: str, user_id: str
) -> dict:
    """Generate WebAuthn ``PublicKeyCredentialCreationOptions``."""
    from webauthn import generate_registration_options
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        ResidentKeyRequirement,
    )

    options = generate_registration_options(
        rp_id=_WEBAUTHN_RP_ID,
        rp_name=_WEBAUTHN_RP_NAME,
        user_id=user_id.encode("utf-8"),
        user_name=email,
        user_display_name=email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
    )
    return options.model_dump(mode="json")


def verify_webauthn_registration(response: dict, expected_challenge: bytes) -> dict:
    """Verify a WebAuthn registration ceremony response."""
    from webauthn import verify_registration_response
    from webauthn.helpers.structs import RegistrationCredential

    credential = RegistrationCredential.model_validate(response)
    verification = verify_registration_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=_WEBAUTHN_RP_ID,
        expected_origin=_WEBAUTHN_ORIGIN,
    )
    return verification.model_dump(mode="json")


def generate_webauthn_authentication_options(user_credentials: list[dict]) -> dict:
    """Generate WebAuthn ``PublicKeyCredentialRequestOptions``."""
    from webauthn import generate_authentication_options

    options = generate_authentication_options(
        rp_id=_WEBAUTHN_RP_ID,
        allow_credentials=user_credentials,
    )
    return options.model_dump(mode="json")


def verify_webauthn_authentication(
    response: dict,
    expected_challenge: bytes,
    credential_public_key: bytes,
    credential_current_sign_count: int,
) -> dict:
    """Verify a WebAuthn authentication ceremony response."""
    from webauthn import verify_authentication_response
    from webauthn.helpers.structs import AuthenticationCredential

    credential = AuthenticationCredential.model_validate(response)
    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=expected_challenge,
        expected_rp_id=_WEBAUTHN_RP_ID,
        expected_origin=_WEBAUTHN_ORIGIN,
        credential_public_key=credential_public_key,
        credential_current_sign_count=credential_current_sign_count,
    )
    return verification.model_dump(mode="json")


# ---------------------------------------------------------------------------
# API key generation & validation
# ---------------------------------------------------------------------------


def generate_api_key() -> Tuple[str, str]:
    """Generate a new API key pair (raw, hashed).

    Returns
    -------
    (raw_key, hashed_key)
        The raw key is shown to the user once; store the hashed key.
    """
    raw = secrets.token_urlsafe(settings.api_key_length)
    prefixed = f"{settings.api_key_prefix}{raw}"
    hashed = hashlib.sha256(prefixed.encode()).hexdigest()
    return prefixed, hashed


def validate_api_key(raw_key: str, hashed_key: str) -> bool:
    """Validate a raw API key against its stored hash."""
    computed = hashlib.sha256(raw_key.encode()).hexdigest()
    return secrets.compare_digest(computed, hashed_key)


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 digest of an API key (for storage comparison)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Encryption (AES-256-GCM for data at rest)
# ---------------------------------------------------------------------------

_ENCRYPTION_KEY: Optional[bytes] = None


def _get_encryption_key() -> bytes:
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is not None:
        return _ENCRYPTION_KEY
    _ENCRYPTION_KEY = settings.encryption_key_bytes
    return _ENCRYPTION_KEY


def encrypt_data(plaintext: str) -> str:
    """Encrypt *plaintext* with AES-256-GCM.

    Returns a base64-encoded string ``nonce$ciphertext``.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_encryption_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"{base64.b64encode(nonce).decode('ascii')}${base64.b64encode(ciphertext).decode('ascii')}"


def decrypt_data(encoded: str) -> str:
    """Decrypt a value previously produced by :func:`encrypt_data`."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_encryption_key()
    nonce_b64, ciphertext_b64 = encoded.split("$", 1)
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# Convenience service class
# ---------------------------------------------------------------------------


class SecurityService:
    """Aggregated security helpers for dependency injection."""

    @staticmethod
    def hash_password(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        return verify_password(password, stored)

    @staticmethod
    def generate_totp_secret() -> str:
        return generate_totp_secret()

    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        return verify_totp(secret, token)

    @staticmethod
    def generate_api_key() -> Tuple[str, str]:
        return generate_api_key()

    @staticmethod
    def validate_api_key(raw: str, hashed: str) -> bool:
        return validate_api_key(raw, hashed)

    @staticmethod
    def encrypt(plaintext: str) -> str:
        return encrypt_data(plaintext)

    @staticmethod
    def decrypt(encoded: str) -> str:
        return decrypt_data(encoded)


security_service = SecurityService()
