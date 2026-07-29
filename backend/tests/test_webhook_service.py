"""Tests for the webhook service layer."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


class TestWebhookService:
    """Tests for WebhookService."""

    @pytest.fixture
    def service(self):
        from app.services.webhook import WebhookService
        return WebhookService()

    @pytest.mark.asyncio
    async def test_create_webhook(self, service):
        """Create a webhook with required fields."""
        webhook = await service.create_webhook(
            user_id=1,
            url="https://example.com/webhook",
            events=["user.created", "search.completed"],
        )
        assert webhook.id == 1
        assert webhook.user_id == 1
        assert webhook.url == "https://example.com/webhook"
        assert webhook.is_active is True
        assert "user.created" in webhook.events

    @pytest.mark.asyncio
    async def test_create_webhook_with_secret(self, service):
        """Create a webhook with an optional secret."""
        webhook = await service.create_webhook(
            user_id=1,
            url="https://example.com/webhook",
            events=["test.event"],
            secret="my-secret-key",
            description="Test webhook",
        )
        assert webhook.secret == "my-secret-key"
        assert webhook.description == "Test webhook"

    @pytest.mark.asyncio
    async def test_get_webhook_returns_none_for_wrong_user(self, service):
        """get_webhook returns None when user_id doesn't match."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        result = await service.get_webhook(webhook_id=1, user_id=2)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_webhook_returns_for_owner(self, service):
        """get_webhook returns the webhook for the owning user."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        result = await service.get_webhook(webhook_id=1, user_id=1)
        assert result is not None
        assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_list_webhooks_returns_owned_only(self, service):
        """list_webhooks only returns webhooks belonging to the user."""
        await service.create_webhook(user_id=1, url="https://a.com", events=["e1"])
        await service.create_webhook(user_id=2, url="https://b.com", events=["e2"])
        await service.create_webhook(user_id=1, url="https://c.com", events=["e3"])

        user1_webhooks = await service.list_webhooks(user_id=1)
        assert len(user1_webhooks) == 2

        user2_webhooks = await service.list_webhooks(user_id=2)
        assert len(user2_webhooks) == 1

    @pytest.mark.asyncio
    async def test_update_webhook_partial(self, service):
        """Update webhook with only url change."""
        await service.create_webhook(user_id=1, url="https://old.com", events=["test"])
        updated = await service.update_webhook(1, 1, url="https://new.com")
        assert updated is not None
        assert updated.url == "https://new.com"
        assert updated.events == ["test"]  # Unchanged

    @pytest.mark.asyncio
    async def test_update_webhook_nonexistent(self, service):
        """Update returns None for non-existent webhook."""
        result = await service.update_webhook(999, user_id=1, url="https://new.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_webhook_deactivate(self, service):
        """Update can deactivate a webhook."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        updated = await service.update_webhook(1, 1, is_active=False)
        assert updated is not None
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_delete_webhook(self, service):
        """Delete webhook returns True and removes it."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        result = await service.delete_webhook(1, 1)
        assert result is True
        assert await service.get_webhook(1, 1) is None

    @pytest.mark.asyncio
    async def test_delete_webhook_wrong_user(self, service):
        """Delete webhook returns False for wrong user."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        result = await service.delete_webhook(1, 2)
        assert result is False

    @pytest.mark.asyncio
    async def test_trigger_event_matches_webhook(self, service):
        """trigger_event delivers to matching webhooks."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["user.created"])
        with patch.object(service, "_deliver_webhook", new_callable=AsyncMock) as mock_deliver:
            await service.trigger_event("user.created", {"id": 1}, user_id=1)
            mock_deliver.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_event_skips_inactive(self, service):
        """trigger_event skips inactive webhooks."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["user.created"])
        await service.update_webhook(1, 1, is_active=False)
        with patch.object(service, "_deliver_webhook", new_callable=AsyncMock) as mock_deliver:
            await service.trigger_event("user.created", {"id": 1}, user_id=1)
            mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_event_skips_wrong_event_type(self, service):
        """trigger_event skips webhooks not subscribed to the event."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["search.completed"])
        with patch.object(service, "_deliver_webhook", new_callable=AsyncMock) as mock_deliver:
            await service.trigger_event("user.created", {"id": 1}, user_id=1)
            mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_event_no_matching_webhooks(self, service):
        """trigger_event with no matches does not raise."""
        await service.trigger_event("unknown.event", {"id": 1}, user_id=1)

    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self, service):
        """Successful delivery marks status as SUCCESS."""
        import httpx
        webhook = await service.create_webhook(
            user_id=1, url="https://example.com/webhook", events=["test"]
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        # Patch the post method on the AsyncClient class itself
        original_post = httpx.AsyncClient.post
        try:
            httpx.AsyncClient.post = AsyncMock(return_value=mock_response)
            with patch("asyncio.sleep", AsyncMock()):
                await service._deliver_webhook(webhook, "test.event", {"key": "val"}, max_retries=1)
                assert len(service._delivery_queue) > 0
                from app.models.webhook import DeliveryStatus
                last_delivery = service._delivery_queue[-1]
                assert last_delivery.status == DeliveryStatus.SUCCESS
        finally:
            httpx.AsyncClient.post = original_post

    @pytest.mark.asyncio
    async def test_deliver_webhook_retries_on_failure(self, service):
        """Failed delivery retries and eventually marks FAILED."""
        import httpx
        webhook = await service.create_webhook(
            user_id=1, url="https://example.com/webhook", events=["test"]
        )
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "error"
        original_post = httpx.AsyncClient.post
        try:
            httpx.AsyncClient.post = AsyncMock(return_value=mock_response)
            with patch("asyncio.sleep", AsyncMock()):
                await service._deliver_webhook(webhook, "test.event", {"key": "val"}, max_retries=1)
                from app.models.webhook import DeliveryStatus
                last_delivery = service._delivery_queue[-1]
                assert last_delivery.status == DeliveryStatus.FAILED
                assert last_delivery.attempts > 0
        finally:
            httpx.AsyncClient.post = original_post

    @pytest.mark.asyncio
    async def test_deliver_webhook_signature(self, service):
        """Delivery with secret includes HMAC signature header."""
        webhook = await service.create_webhook(
            user_id=1, url="https://httpbin.org/post", events=["test"], secret="test-secret"
        )
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "ok"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            await service._deliver_webhook(webhook, "test.event", {"key": "val"})

            call_kwargs = mock_client.return_value.__aenter__.return_value.post.call_args[1]
            assert "X-Webhook-Signature" in call_kwargs["headers"]
            assert call_kwargs["headers"]["X-Webhook-Signature"].startswith("sha256=")

    @pytest.mark.asyncio
    async def test_test_webhook_success(self, service):
        """test_webhook sends a test event."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        with patch.object(service, "_deliver_webhook", new_callable=AsyncMock) as mock_deliver:
            mock_deliver.return_value = None
            result = await service.test_webhook(1, 1)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_test_webhook_not_found(self, service):
        """test_webhook returns error for non-existent webhook."""
        result = await service.test_webhook(999, 1)
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_delivery_logs(self, service):
        """get_delivery_logs returns most recent deliveries."""
        from app.models.webhook import WebhookDeliveryDB, DeliveryStatus
        webhook = await service.create_webhook(
            user_id=1, url="https://example.com", events=["test"]
        )
        delivery = WebhookDeliveryDB(
            id=1, webhook_id=webhook.id, event_type="test",
            payload={}, status=DeliveryStatus.SUCCESS,
            response_code=200, response_body="ok",
            attempts=1, next_retry=datetime.now(), created_at=datetime.now(),
        )
        service._delivery_queue.append(delivery)

        logs = await service.get_delivery_logs(1, 1)
        assert len(logs) == 1
        assert logs[0].id == 1

    @pytest.mark.asyncio
    async def test_get_delivery_logs_wrong_user(self, service):
        """get_delivery_logs returns empty for wrong user."""
        await service.create_webhook(user_id=1, url="https://example.com", events=["test"])
        logs = await service.get_delivery_logs(1, 2)
        assert logs == []