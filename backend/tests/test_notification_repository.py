"""Tests for backend/app/database/repositories/notification.py.

Coverage areas:
- Notification creation and storage
- Notification retrieval (list_for_user, get_unread_count)
- Read status management (mark_read, mark_all_read)
- Notification deletion
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock

from app.database.repositories.notification import NotificationRepository


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    async def fetchone(self):
        return self._row

    async def fetchall(self):
        return list(self._rows)


class FakeDB:
    def __init__(self):
        self.committed = False
        self.executed_queries = []
        self._rows_by_query = {}

    async def execute(self, sql, args=None):
        self.executed_queries.append((sql, args))
        return FakeCursor()

    async def commit(self):
        self.committed = True

    async def fetchone(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        rows = self._rows_by_query.get(query_key, [{}])
        return rows[0] if rows else None

    async def fetchall(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        return list(self._rows_by_query.get(query_key, []))


@pytest.fixture
def repo():
    db = FakeDB()
    return NotificationRepository(db)


class TestNotificationCreation:
    """Test notification creation operations."""

    @pytest.mark.asyncio
    async def test_create_notification(self, repo):
        """Should create a new notification."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="Test Notification",
            message="This is a test notification",
            data={"key": "value"},
        )
        assert notif_id >= 0
        assert repo._db.committed is True
        assert any("INSERT INTO notifications" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_create_notification_no_data(self, repo):
        """Should create notification without data."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="Test",
            message="Message without data",
            data=None,
        )
        assert notif_id >= 0
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_create_notification_empty_data(self, repo):
        """Should handle empty dict as data."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="warning",
            category="storage",
            title="Storage Warning",
            message="Near capacity",
            data={},
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_create_notification_with_complex_data(self, repo):
        """Should handle complex data dict."""
        complex_data = {
            "documents": [1, 2, 3],
            "threshold": 80.5,
            "expires": "2024-12-31",
            "nested": {"key": "value"},
        }
        notif_id = await repo.create(
            user_id=1,
            notif_type="warning",
            category="analytics",
            title="Analytics Ready",
            message="Your analytics are ready",
            data=complex_data,
        )
        assert notif_id >= 0


class TestNotificationRetrieval:
    """Test notification retrieval operations."""

    @pytest.mark.asyncio
    async def test_list_for_user(self, repo):
        """Should list notifications for user."""
        repo._db._rows_by_query[("SELECT id, type, category, title, message, data, is_read, "
            "read_at, created_at, expires_at "
            "FROM notifications WHERE user_id = ? AND is_deleted = FALSE "
            "ORDER BY created_at DESC LIMIT ?", (1, 50))] = [
            {"id": 1, "title": "Notification 1", "is_read": False},
            {"id": 2, "title": "Notification 2", "is_read": True},
        ]
        notifications = await repo.list_for_user(1, limit=50)
        assert len(notifications) == 2
        assert notifications[0]["title"] == "Notification 1"

    @pytest.mark.asyncio
    async def test_list_for_user_empty(self, repo):
        """Should return empty list when user has no notifications."""
        repo._db._rows_by_query[("SELECT id, type, category, title, message, data, is_read, "
            "read_at, created_at, expires_at "
            "FROM notifications WHERE user_id = ? AND is_deleted = FALSE "
            "ORDER BY created_at DESC LIMIT ?", (999, 50))] = []
        notifications = await repo.list_for_user(999, limit=50)
        assert notifications == []

    @pytest.mark.asyncio
    async def test_list_for_user_with_limit(self, repo):
        """Should respect limit parameter."""
        # Add a mock that also records queries
        original_fetchall = repo._db.fetchall
        async def mock_fetchall(sql, args=None):
            repo._db.executed_queries.append((sql, args))
            return []
        repo._db.fetchall = mock_fetchall
        
        await repo.list_for_user(1, limit=10)
        executed = repo._db.executed_queries[-1]
        assert "LIMIT ?" in executed[0]

    @pytest.mark.asyncio
    async def test_list_for_user_default_limit(self, repo):
        """Should use default limit of 50."""
        # Add a mock that also records queries
        original_fetchall = repo._db.fetchall
        async def mock_fetchall(sql, args=None):
            repo._db.executed_queries.append((sql, args))
            return []
        repo._db.fetchall = mock_fetchall
        
        await repo.list_for_user(1)
        executed = repo._db.executed_queries[-1]
        assert "50" in executed[1] or 50 in executed[1]

    @pytest.mark.asyncio
    async def test_list_for_user_unread_only(self, repo):
        """Should list only unread notifications."""
        repo._db._rows_by_query[("SELECT id, type, category, title, message, data, is_read, "
            "read_at, created_at, expires_at "
            "FROM notifications WHERE user_id = ? AND is_deleted = FALSE "
            "AND is_read = FALSE "
            "ORDER BY created_at DESC LIMIT ?", (1, 50))] = [
            {"id": 1, "title": "Unread", "is_read": False}
        ]
        notifications = await repo.list_for_user(1, limit=50, unread_only=True)
        assert len(notifications) == 1
        assert notifications[0]["is_read"] is False


class TestUnreadCount:
    """Test unread notification count operations."""

    @pytest.mark.asyncio
    async def test_get_unread_count(self, repo):
        """Should get count of unread notifications."""
        repo._db._rows_by_query[("SELECT COUNT(*) as cnt FROM notifications "
            "WHERE user_id = ? AND is_read = FALSE AND is_deleted = FALSE", (1,))] = [
            {"cnt": 5}
        ]
        count = await repo.get_unread_count(1)
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_unread_count_empty(self, repo):
        """Should return 0 when no unread notifications."""
        repo._db._rows_by_query[("SELECT COUNT(*) as cnt FROM notifications "
            "WHERE user_id = ? AND is_read = FALSE AND is_deleted = FALSE", (1,))] = [
            {"cnt": 0}
        ]
        count = await repo.get_unread_count(1)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_unread_count_all_read(self, repo):
        """Should return 0 when all notifications are read."""
        repo._db._rows_by_query[("SELECT COUNT(*) as cnt FROM notifications "
            "WHERE user_id = ? AND is_read = FALSE AND is_deleted = FALSE", (999,))] = [
            {"cnt": 0}
        ]
        count = await repo.get_unread_count(999)
        assert count == 0


class TestReadStatus:
    """Test notification read status management."""

    @pytest.mark.asyncio
    async def test_mark_read(self, repo):
        """Should mark notification as read."""
        await repo.mark_read(notif_id=1, user_id=1)
        assert repo._db.committed is True
        assert any("is_read = TRUE" in q[0] for q in repo._db.executed_queries)
        assert any("read_at = ?" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self, repo):
        """Should handle marking non-existent notification as read."""
        # mark_read doesn't verify existence, so it should still commit
        await repo.mark_read(notif_id=999, user_id=1)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_mark_read_wrong_user(self, repo):
        """Should handle marking another user's notification."""
        await repo.mark_read(notif_id=1, user_id=2)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_mark_all_read(self, repo):
        """Should mark all user's notifications as read."""
        await repo.mark_all_read(1)
        assert repo._db.committed is True
        assert any("is_read = TRUE" in q[0] for q in repo._db.executed_queries)
        assert any("is_read = FALSE" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_mark_all_read_empty(self, repo):
        """Should handle user with no notifications."""
        await repo.mark_all_read(999)
        assert repo._db.committed is True


class TestNotificationDeletion:
    """Test notification deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_notification(self, repo):
        """Should soft delete a notification."""
        await repo.delete(notif_id=1, user_id=1)
        assert repo._db.committed is True
        assert any("is_deleted = TRUE" in q[0] for q in repo._db.executed_queries)
        assert any("deleted_at = ?" in q[0] for q in repo._db.executed_queries)

    @pytest.mark.asyncio
    async def test_delete_notification_not_found(self, repo):
        """Should handle deletion of non-existent notification."""
        await repo.delete(notif_id=999, user_id=1)
        assert repo._db.committed is True

    @pytest.mark.asyncio
    async def test_delete_notification_wrong_user(self, repo):
        """Should handle deletion of another user's notification."""
        await repo.delete(notif_id=1, user_id=2)
        assert repo._db.committed is True


class TestNotificationTypes:
    """Test different notification types and categories."""

    @pytest.mark.asyncio
    async def test_create_info_notification(self, repo):
        """Should create info type notification."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="Info",
            message="Info message",
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_create_warning_notification(self, repo):
        """Should create warning type notification."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="warning",
            category="storage",
            title="Warning",
            message="Warning message",
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_create_error_notification(self, repo):
        """Should create error type notification."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="error",
            category="indexing",
            title="Error",
            message="Error message",
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_create_custom_category(self, repo):
        """Should create notification with custom category."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="custom_category",
            title="Custom",
            message="Custom message",
        )
        assert notif_id >= 0


class TestNotificationExpiration:
    """Test notification expiration handling."""

    @pytest.mark.asyncio
    async def test_create_with_expires_at(self, repo):
        """Should create notification with expiration."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="Expires Soon",
            message="This will expire",
            data={"expires_at": "2024-12-31"},
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_list_with_expiration_data(self, repo):
        """Should return notifications with expiration data."""
        repo._db._rows_by_query[("SELECT id, type, category, title, message, data, is_read, "
            "read_at, created_at, expires_at "
            "FROM notifications WHERE user_id = ? AND is_deleted = FALSE "
            "ORDER BY created_at DESC LIMIT ?", (1, 50))] = [
            {"id": 1, "title": "Expiring", "data": '{"expires_at": "2024-12-31"}', "expires_at": None}
        ]
        notifications = await repo.list_for_user(1)
        assert len(notifications) == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_create_with_long_title(self, repo):
        """Should handle long title."""
        long_title = "A" * 1000
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title=long_title,
            message="Message",
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_create_with_long_message(self, repo):
        """Should handle long message."""
        long_message = "B" * 5000
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="Title",
            message=long_message,
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_list_for_user_special_characters(self, repo):
        """Should handle notifications with special characters in title."""
        repo._db._rows_by_query[("SELECT id, type, category, title, message, data, is_read, "
            "read_at, created_at, expires_at "
            "FROM notifications WHERE user_id = ? AND is_deleted = FALSE "
            "ORDER BY created_at DESC LIMIT ?", (1, 50))] = [
            {"id": 1, "title": "Title with 'quotes' and \"double\"", "is_read": False}
        ]
        notifications = await repo.list_for_user(1)
        assert notifications[0]["title"] == "Title with 'quotes' and \"double\""

    @pytest.mark.asyncio
    async def test_create_with_unicode(self, repo):
        """Should handle Unicode characters."""
        notif_id = await repo.create(
            user_id=1,
            notif_type="info",
            category="system",
            title="测试通知 🌟",
            message="Unicode message 日本語",
        )
        assert notif_id >= 0

    @pytest.mark.asyncio
    async def test_multiple_operations_same_notification(self, repo):
        """Should handle multiple operations on same notification."""
        # Create, mark read, delete
        notif_id = await repo.create(1, "info", "system", "Test", "Msg")
        await repo.mark_read(notif_id, 1)
        await repo.delete(notif_id, 1)
        assert repo._db.committed is True
        assert len([q for q in repo._db.executed_queries if "INSERT INTO notifications" in q[0]]) == 1
        assert len([q for q in repo._db.executed_queries if "UPDATE notifications SET is_read" in q[0]]) == 1
        assert len([q for q in repo._db.executed_queries if "UPDATE notifications SET is_deleted" in q[0]]) == 1

    @pytest.mark.asyncio
    async def test_mark_all_read_no_notifications(self, repo):
        """Should handle mark_all_read for user with no notifications."""
        # Query for unread should return 0 rows, but mark_all_read should still execute
        await repo.mark_all_read(999)
        assert repo._db.committed is True
        # Verify UPDATE query was executed
        assert any("UPDATE notifications SET is_read = TRUE" in q[0] for q in repo._db.executed_queries)