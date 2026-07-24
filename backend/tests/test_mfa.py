"""Tests for app/services/mfa.py — TOTP/2FA service."""


class TestMFAService:
    """Tests for MFAService."""

    def test_generate_secret(self):
        """Primary success path: generate a secret key."""
        from app.services.mfa import MFAService
        secret = MFAService.generate_secret()
        assert secret is not None
        assert len(secret) > 0
        assert isinstance(secret, str)

    def test_get_totp_uri(self):
        """Primary success path: generate TOTP URI."""
        from app.services.mfa import MFAService
        uri = MFAService.get_totp_uri("JBSWY3DPEHPK3PXP", "test@example.com", issuer="Nebula")
        assert "test" in uri
        assert "example.com" in uri
        assert "Nebula" in uri
        assert "otpauth://" in uri

    def test_generate_qr_code(self):
        """Primary success path: generate QR code bytes."""
        from app.services.mfa import MFAService
        uri = "otpauth://totp/Nebula:test@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Nebula"
        qr_bytes = MFAService.generate_qr_code(uri)
        assert qr_bytes is not None
        assert len(qr_bytes) > 0
        assert qr_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_verify_token_valid(self):
        """Primary success path: verify a valid TOTP token."""
        from app.services.mfa import MFAService
        import pyotp
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        assert MFAService.verify_token(secret, token) is True

    def test_verify_token_invalid(self):
        """Failure path: verify an invalid TOTP token."""
        from app.services.mfa import MFAService
        assert MFAService.verify_token("JBSWY3DPEHPK3PXP", "000000") is False

    def test_generate_backup_codes(self):
        """Primary success path: generate backup codes."""
        from app.services.mfa import MFAService
        codes = MFAService.generate_backup_codes(count=5)
        assert len(codes) == 5
        for code in codes:
            assert len(code) == 9
            assert "-" in code

    def test_generate_backup_codes_default_count(self):
        """Primary success path: default 10 backup codes."""
        from app.services.mfa import MFAService
        codes = MFAService.generate_backup_codes()
        assert len(codes) == 10

    def test_hash_backup_code(self):
        """Primary success path: hash backup code."""
        from app.services.mfa import MFAService
        hashed = MFAService.hash_backup_code("ABCD-1234")
        assert hashed is not None
        assert len(hashed) == 64
        assert isinstance(hashed, str)

    def test_hash_backup_code_normalizes_dashes(self):
        """Edge case: hash normalizes dashes and case."""
        from app.services.mfa import MFAService
        hashed1 = MFAService.hash_backup_code("ABCD-1234")
        hashed2 = MFAService.hash_backup_code("abcd-1234")
        assert hashed1 == hashed2

    def test_verify_backup_code_valid(self):
        """Primary success path: verify valid backup code."""
        from app.services.mfa import MFAService
        code = "ABCD-1234"
        hashed = MFAService.hash_backup_code(code)
        assert MFAService.verify_backup_code(code, hashed) is True

    def test_verify_backup_code_invalid(self):
        """Failure path: verify invalid backup code."""
        from app.services.mfa import MFAService
        hashed = MFAService.hash_backup_code("ABCD-1234")
        assert MFAService.verify_backup_code("XXXX-9999", hashed) is False


class TestMFAEnrollment:
    """Tests for MFA enrollment."""

    def test_enroll_mfa(self):
        """Primary success path: enroll MFA."""
        from app.services.mfa import enroll_mfa
        enrollment = enroll_mfa("test@example.com")
        assert enrollment.secret is not None
        assert enrollment.qr_code is not None
        assert len(enrollment.qr_code) > 0
        assert len(enrollment.backup_codes) == 10
        assert len(enrollment.backup_codes_hashed) == 10

    def test_enroll_mfa_qr_content(self):
        """Verify QR code contains valid TOTP URI."""
        from app.services.mfa import enroll_mfa
        enrollment = enroll_mfa("test@example.com")
        assert enrollment.qr_code[:8] == b'\x89PNG\r\n\x1a\n'


class TestVerifyMFAToken:
    """Tests for verify_mfa_token function."""

    def test_verify_mfa_token_valid(self):
        """Primary success path: verify valid TOTP token."""
        from app.services.mfa import verify_mfa_token, MFAService
        import pyotp
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        is_valid, error = verify_mfa_token(secret, token)
        assert is_valid is True
        assert error == ""

    def test_verify_mfa_token_invalid(self):
        """Failure path: verify invalid token."""
        from app.services.mfa import verify_mfa_token
        is_valid, error = verify_mfa_token("JBSWY3DPEHPK3PXP", "000000")
        assert is_valid is False
        assert "Invalid" in error

    def test_verify_mfa_token_backup_code_rejected(self):
        """Edge case: backup code token rejected."""
        from app.services.mfa import verify_mfa_token
        is_valid, error = verify_mfa_token("secret", "ABCD1234")
        assert is_valid is False
        assert "backup code" in error.lower()

    def test_verify_mfa_token_bad_format(self):
        """Failure path: token with wrong length."""
        from app.services.mfa import verify_mfa_token
        is_valid, error = verify_mfa_token("secret", "123")
        assert is_valid is False

    def test_verify_mfa_token_non_digit(self):
        """Failure path: non-digit characters in token."""
        from app.services.mfa import verify_mfa_token
        is_valid, error = verify_mfa_token("secret", "12A456")
        assert is_valid is False

    def test_verify_mfa_token_removes_spaces(self):
        """Edge case: token with spaces becomes valid 6-digit after stripping."""
        from app.services.mfa import verify_mfa_token, MFAService
        import pyotp
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        token = totp.now()
        spaced = token[:3] + " " + token[3:]
        is_valid, error = verify_mfa_token(secret, spaced)
        assert is_valid is True