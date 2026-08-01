"""Tests for backend/app/services/email.py.

Coverage areas:
- Email sending with SMTP
- Email templates (verification, password reset, welcome, MFA, security)
- Disabled email service handling
- Error handling for SMTP failures
"""

from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email import EmailService, email_service


class TestEmailServiceInitialization:
    """Test email service initialization."""

    def test_email_service_enabled(self):
        """Should enable service when SMTP is configured."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_name = "Nebula"
            mock_settings.smtp_from_email = "noreply@example.com"

            with patch("app.services.email.logger"):
                service = EmailService()
                assert service.enabled is True

    def test_email_service_disabled_no_host(self):
        """Should disable service when SMTP host is not configured."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = ""
            mock_settings.smtp_username = ""

            with patch("app.services.email.logger") as mock_logger:
                service = EmailService()
                assert service.enabled is False
                mock_logger.warning.assert_called()

    def test_email_service_disabled_no_username(self):
        """Should disable service when SMTP username is not configured."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_username = ""

            with patch("app.services.email.logger") as mock_logger:
                service = EmailService()
                assert service.enabled is False
                mock_logger.warning.assert_called()


class TestSendEmail:
    """Test email sending functionality."""

    @pytest.mark.asyncio
    async def test_send_email_disabled_service(self):
        """Should return False when service is disabled."""
        service = EmailService()
        service.enabled = False

        result = await service.send_email(
            to_email="user@example.com",
            subject="Test Subject",
            html_content="<p>Test</p>",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Should send email successfully."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_use_tls = True
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_name = "Nebula"
            mock_settings.smtp_from_email = "noreply@example.com"

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                with patch("app.services.email.logger") as mock_logger:
                    result = await service.send_email(
                        to_email="user@example.com",
                        subject="Test Subject",
                        html_content="<p>Test HTML</p>",
                        text_content="Test Text",
                    )

                    assert result is True
                    mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_smtp_error(self):
        """Should handle SMTP errors gracefully."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_smtp.side_effect = Exception("Connection failed")

                with patch("app.services.email.logger") as mock_logger:
                    result = await service.send_email(
                        to_email="user@example.com",
                        subject="Test Subject",
                        html_content="<p>Test</p>",
                    )

                    assert result is False
                    mock_logger.exception.assert_called()

    @pytest.mark.asyncio
    async def test_send_email_without_tls(self):
        """Should handle SMTP without TLS."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 25
            mock_settings.smtp_use_tls = False
            mock_settings.smtp_username = ""
            mock_settings.smtp_password = ""

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await service.send_email(
                    to_email="user@example.com",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

                assert result is True
                # starttls should not be called
                mock_server.starttls.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_email_no_login(self):
        """Should send without login when credentials not provided."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_use_tls = True
            mock_settings.smtp_username = ""
            mock_settings.smtp_password = ""

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await service.send_email(
                    to_email="user@example.com",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

                assert result is True
                mock_server.login.assert_not_called()


class TestEmailTemplates:
    """Test email template content."""

    @pytest.mark.asyncio
    async def test_verification_email_content(self):
        """Should generate correct verification email."""
        service = EmailService()

        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_verification_email(
                to_email="user@example.com",
                verification_link="https://example.com/verify?token=abc123",
            )

            assert result is True
            mock_send.assert_called_once()

            # Verify email structure
            call_kwargs = mock_send.call_args[1]
            assert "Verify your Nebula Search account" in call_kwargs["subject"]
            assert "Please verify your email address" in call_kwargs["html_content"]
            assert "https://example.com/verify?token=abc123" in call_kwargs["html_content"]
            assert call_kwargs["text_content"] is not None
            assert "24 hours" in call_kwargs["text_content"]

    @pytest.mark.asyncio
    async def test_password_reset_email_content(self):
        """Should generate correct password reset email."""
        service = EmailService()

        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_password_reset_email(
                to_email="user@example.com",
                reset_link="https://example.com/reset?token=xyz789",
            )

            assert result is True
            mock_send.assert_called_once()

            call_kwargs = mock_send.call_args[1]
            assert "Reset your Nebula Search password" in call_kwargs["subject"]
            assert "Reset Password" in call_kwargs["html_content"]
            assert "https://example.com/reset?token=xyz789" in call_kwargs["html_content"]
            assert "1 hour" in call_kwargs["text_content"]

    @pytest.mark.asyncio
    async def test_welcome_email_content(self):
        """Should generate correct welcome email."""
        service = EmailService()

        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_welcome_email(
                to_email="user@example.com",
            )

            assert result is True
            mock_send.assert_called_once()

            call_kwargs = mock_send.call_args[1]
            assert "Welcome to Nebula Search!" in call_kwargs["subject"]
            assert "Thank you for creating an account" in call_kwargs["html_content"]
            assert "Getting Started" in call_kwargs["html_content"]
            assert "AI-powered search" in call_kwargs["text_content"]

    @pytest.mark.asyncio
    async def test_mfa_enabled_email_content(self):
        """Should generate correct MFA enabled email."""
        service = EmailService()

        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_mfa_enabled_email(
                to_email="user@example.com",
            )

            assert result is True
            mock_send.assert_called_once()

            call_kwargs = mock_send.call_args[1]
            assert "Multi-Factor Authentication Enabled" in call_kwargs["subject"]
            assert "MFA Enabled" in call_kwargs["html_content"]
            assert "more secure" in call_kwargs["html_content"]

    @pytest.mark.asyncio
    async def test_security_alert_email_content(self):
        """Should generate correct security alert email."""
        service = EmailService()

        with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_security_alert(
                to_email="user@example.com",
                alert_type="New Login",
                details="New login from 192.168.1.1",
            )

            assert result is True
            mock_send.assert_called_once()

            call_kwargs = mock_send.call_args[1]
            assert "Security Alert: New Login" in call_kwargs["subject"]
            assert "<strong>New Login</strong>" in call_kwargs["html_content"]
            assert "New login from 192.168.1.1" in call_kwargs["html_content"]
            assert "Change your password" in call_kwargs["html_content"]


class TestGlobalInstance:
    """Test global email service instance."""

    def test_global_email_service(self):
        """Global instance should exist."""
        assert email_service is not None
        assert isinstance(email_service, EmailService)
        # Should be disabled in test environment
        assert email_service.enabled is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_send_email_empty_to_email(self):
        """Should handle empty to_email."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await service.send_email(
                    to_email="",
                    subject="Test Subject",
                    html_content="<p>Test</p>",
                )

                # Should succeed if SMTP accepts empty email
                assert result is True

    @pytest.mark.asyncio
    async def test_send_email_empty_content(self):
        """Should handle empty HTML content."""
        service = EmailService()

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587

            with patch("app.services.email.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = await service.send_email(
                    to_email="user@example.com",
                    subject="Test Subject",
                    html_content="",
                )

                # Should succeed with empty content
                assert result is True