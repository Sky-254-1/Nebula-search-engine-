"""Tests for app/routes/auth_extended.py — email verification, password reset, account management."""

import pytest


class APITestBase:
    """Bind module-scoped TestClient to test class instances."""

    @pytest.fixture(autouse=True)
    def _bind_client(self, client):
        self.client = client


class TestEmailVerification(APITestBase):
    """Test email verification endpoints."""

    def test_verify_email_missing_token(self):
        """GET /verify-email without token returns 422."""
        response = self.client.get("/api/v1/auth/verify-email")
        assert response.status_code == 422

    def test_verify_email_invalid_token(self):
        """GET /verify-email with invalid token returns 400."""
        response = self.client.get("/api/v1/auth/verify-email", params={"token": "invalid"})
        assert response.status_code == 400

    def test_resend_verification_unauthorized(self):
        """POST /resend-verification without auth returns 401."""
        response = self.client.post("/api/v1/auth/resend-verification")
        assert response.status_code == 401


class TestPasswordReset(APITestBase):
    """Test password reset endpoints."""

    def test_forgot_password_no_email(self):
        """POST /forgot-password without email returns 422."""
        response = self.client.post("/api/v1/auth/forgot-password", json={})
        assert response.status_code == 422

    def test_forgot_password_invalid_email(self):
        """POST /forgot-password with invalid email returns 422."""
        response = self.client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422

    def test_reset_password_no_token(self):
        """POST /reset-password without token returns 422."""
        response = self.client.post("/api/v1/auth/reset-password", json={})
        assert response.status_code == 422

    def test_reset_password_invalid_token(self):
        """POST /reset-password with invalid token returns 400."""
        response = self.client.post(
            "/api/v1/auth/reset-password",
            params={"token": "invalid", "new_password": "NewPass123!"},
        )
        assert response.status_code == 400


class TestAccountManagement(APITestBase):
    """Test account management endpoints."""

    def test_change_password_unauthorized(self):
        """POST /change-password without auth returns 401."""
        response = self.client.post("/api/v1/auth/change-password")
        assert response.status_code == 401

    def test_change_email_unauthorized(self):
        """POST /change-email without auth returns 401."""
        response = self.client.post("/api/v1/auth/change-email")
        assert response.status_code == 401

    def test_delete_account_unauthorized(self):
        """DELETE /account without auth returns 401."""
        response = self.client.delete("/api/v1/auth/account")
        assert response.status_code == 401

    def test_get_sessions_unauthorized(self):
        """GET /sessions without auth returns 401."""
        response = self.client.get("/api/v1/auth/sessions")
        assert response.status_code == 401

    def test_terminate_session_unauthorized(self):
        """DELETE /sessions/{id} without auth returns 401."""
        response = self.client.delete("/api/v1/auth/sessions/some-id")
        assert response.status_code == 401


