"""Tests for backend/app/database/repositories/collection.py.

Coverage areas:
- Collection CRUD operations (create, get_by_id, list_for_user, update, delete)
- Collection item operations (add_item, list_items, remove_item)
- Item count tracking
- Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock

from app.database.repositories.collection import CollectionRepository


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []
        self.lastrowid = 1 if row else 0

    async def fetchone(self):
        return self._row

    async def fetchall(self):
        return list(self._rows)


class FakeDB:
    def __init__(self):
        self.committed = False
        self.executed_queries = []
        self.fetchone_queries = []
        self.fetchall_queries = []
        self._rows_by_query = {}

    async def execute(self, sql, args=None):
        self.executed_queries.append((sql, args))
        return FakeCursor()

    async def commit(self):
        self.committed = True

    async def fetchone(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        self.fetchone_queries.append((sql, args))
        
        # Track in executed_queries for backwards compatibility
        if any(cmd in sql.upper() for cmd in ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"]):
            self.executed_queries.append((sql, args))
        
        # Handle INSERT...RETURNING by returning a mock row with lastrowid
        if "INSERT INTO" in sql and "RETURNING" in sql:
            # Return a mock row with id=1
            return {"id": 1}
        
        rows = self._rows_by_query.get(query_key, [{}])
        return rows[0] if rows else None

    async def fetchall(self, sql, args=None):
        query_key = (sql, tuple(args) if args else ())
        self.fetchall_queries.append((sql, args))
        
        # Track in executed_queries for backwards compatibility
        if any(cmd in sql.upper() for cmd in ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"]):
            self.executed_queries.append((sql, args))
        
        rows = self._rows_by_query.get(query_key, [])
        return list(rows)


@pytest.fixture
def repo():
    db = FakeDB()
    return CollectionRepository(db)


class TestCollectionCRUD:
    """Test collection CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_collection(self, repo):
        """Should create a new collection."""
        collection_id = await repo.create(
            user_id=1,
            name="My Collection",
            description="A test collection",
            is_public=False,
        )
        assert collection_id is not None
        assert collection_id >= 0
        assert repo.db.committed is True
        assert any("INSERT INTO collections" in q[0] for q in repo.db.executed_queries)

    @pytest.mark.asyncio
    async def test_create_collection_no_description(self, repo):
        """Should create collection without description."""
        collection_id = await repo.create(
            user_id=1,
            name="Another Collection",
            description=None,
            is_public=True,
        )
        assert collection_id is not None

    @pytest.mark.asyncio
    async def test_list_for_user(self, repo):
        """Should list collections for a user."""
        repo.db._rows_by_query[(("""SELECT c.*, (SELECT COUNT(*) FROM collection_items ci WHERE ci.collection_id = c.id) as item_count
               FROM collections c WHERE c.user_id = ? ORDER BY c.updated_at DESC""",
            (1,)))] = [
            {"id": 1, "name": "Collection 1", "item_count": 5},
            {"id": 2, "name": "Collection 2", "item_count": 3},
        ]
        collections = await repo.list_for_user(1)
        assert len(collections) == 2
        assert collections[0]["name"] == "Collection 1"
        assert collections[0]["item_count"] == 5

    @pytest.mark.asyncio
    async def test_list_for_user_empty(self, repo):
        """Should return empty list when user has no collections."""
        repo.db._rows_by_query[(("""SELECT c.*, (SELECT COUNT(*) FROM collection_items ci WHERE ci.collection_id = c.id) as item_count
               FROM collections c WHERE c.user_id = ? ORDER BY c.updated_at DESC""",
            (999,)))] = []
        collections = await repo.list_for_user(999)
        assert collections == []

    @pytest.mark.asyncio
    async def test_get_by_id(self, repo):
        """Should retrieve collection by ID."""
        repo.db._rows_by_query[("SELECT * FROM collections WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "name": "My Collection"}
        ]
        repo.db._rows_by_query[("SELECT COUNT(*) as cnt FROM collection_items WHERE collection_id = ?",
            (1,))] = [{"cnt": 5}]
        
        collection = await repo.get_by_id(1, 1)
        assert collection is not None
        assert collection["id"] == 1
        assert collection["item_count"] == 5

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo):
        """Should return None when collection not found."""
        repo.db._rows_by_query[("SELECT * FROM collections WHERE id = ? AND user_id = ?",
            (999, 1))] = []
        collection = await repo.get_by_id(999, 1)
        assert collection is None

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_user(self, repo):
        """Should return None when accessing another user's collection."""
        repo.db._rows_by_query[("SELECT * FROM collections WHERE id = ? AND user_id = ?",
            (1, 2))] = []
        collection = await repo.get_by_id(1, 2)
        assert collection is None

    @pytest.mark.asyncio
    async def test_update_collection(self, repo):
        """Should update collection."""
        await repo.update(1, 1, name="Updated Name", is_public=True)
        assert repo.db.committed is True
        assert any("UPDATE collections SET" in q[0] for q in repo.db.executed_queries)

    @pytest.mark.asyncio
    async def test_update_collection_no_changes(self, repo):
        """Should handle update with no changes."""
        # All None values should not generate any UPDATE
        await repo.update(1, 1, name=None, description=None)
        # No committed changes expected
        assert repo.db.committed is False

    @pytest.mark.asyncio
    async def test_update_collection_partial(self, repo):
        """Should update only provided fields."""
        await repo.update(1, 1, name="New Name")
        assert repo.db.committed is True
        update_query = [q for q in repo.db.executed_queries if "UPDATE collections SET" in q[0]]
        assert len(update_query) == 1
        assert "name = ?" in update_query[0][0]

    @pytest.mark.asyncio
    async def test_delete_collection(self, repo):
        """Should delete collection and its items."""
        await repo.delete(1, 1)
        assert repo.db.committed is True
        assert any("DELETE FROM collection_items" in q[0] for q in repo.db.executed_queries)
        assert any("DELETE FROM collections" in q[0] for q in repo.db.executed_queries)

    @pytest.mark.asyncio
    async def test_delete_collection_not_found(self, repo):
        """Should handle deletion of non-existent collection."""
        # delete method doesn't check if collection exists
        await repo.delete(999, 1)
        assert repo.db.committed is True


class TestCollectionItemOperations:
    """Test collection item operations."""

    @pytest.mark.asyncio
    async def test_add_item_with_document(self, repo):
        """Should add item with document reference."""
        item_id = await repo.add_item(
            collection_id=1,
            document_id=5,
            search_result_id=None,
            note="Important document",
        )
        assert item_id is not None
        assert item_id >= 0
        assert repo.db.committed is True
        assert any("INSERT INTO collection_items" in q[0] for q in repo.db.executed_queries)

    @pytest.mark.asyncio
    async def test_add_item_with_search_result(self, repo):
        """Should add item with search result reference."""
        item_id = await repo.add_item(
            collection_id=1,
            document_id=None,
            search_result_id=100,
            note="Search result",
        )
        assert item_id is not None

    @pytest.mark.asyncio
    async def test_add_item_without_note(self, repo):
        """Should add item without note."""
        item_id = await repo.add_item(
            collection_id=1,
            document_id=5,
            search_result_id=None,
            note=None,
        )
        assert item_id is not None

    @pytest.mark.asyncio
    async def test_add_item_with_both_references(self, repo):
        """Should handle item with both document and search result."""
        item_id = await repo.add_item(
            collection_id=1,
            document_id=5,
            search_result_id=100,
            note="Both references",
        )
        assert item_id is not None

    @pytest.mark.asyncio
    async def test_list_items(self, repo):
        """Should list items in a collection."""
        repo.db._rows_by_query[("SELECT * FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC",
            (1,))] = [
            {"id": 1, "document_id": 5, "search_result_id": None, "note": "Note 1"},
            {"id": 2, "document_id": None, "search_result_id": 100, "note": "Note 2"},
        ]
        items = await repo.list_items(1)
        assert len(items) == 2
        assert items[0]["note"] == "Note 1"

    @pytest.mark.asyncio
    async def test_list_items_empty(self, repo):
        """Should return empty list when collection has no items."""
        repo.db._rows_by_query[("SELECT * FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC",
            (999,))] = []
        items = await repo.list_items(999)
        assert items == []

    @pytest.mark.asyncio
    async def test_remove_item(self, repo):
        """Should remove item from collection."""
        await repo.remove_item(1)
        assert repo.db.committed is True
        assert any("DELETE FROM collection_items WHERE id = ?" in q[0] for q in repo.db.executed_queries)

    @pytest.mark.asyncio
    async def test_remove_item_not_found(self, repo):
        """Should handle removal of non-existent item."""
        await repo.remove_item(999)
        assert repo.db.committed is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_create_collection_with_special_chars(self, repo):
        """Should handle collection names with special characters."""
        collection_id = await repo.create(
            user_id=1,
            name="Collection with 'quotes' and \"double quotes\"",
            description="Description with <html> tags",
            is_public=False,
        )
        assert collection_id is not None

    @pytest.mark.asyncio
    async def test_list_for_user_with_limit(self, repo):
        """Should order by updated_at descending."""
        repo.db._rows_by_query[(("""SELECT c.*, (SELECT COUNT(*) FROM collection_items ci WHERE ci.collection_id = c.id) as item_count
               FROM collections c WHERE c.user_id = ? ORDER BY c.updated_at DESC""",
            (1,)))] = []
        await repo.list_for_user(1)
        executed = repo.db.executed_queries[-1]
        assert "ORDER BY c.updated_at DESC" in executed[0]

    @pytest.mark.asyncio
    async def test_update_with_empty_kwargs(self, repo):
        """Should handle empty kwargs dict."""
        # Empty kwargs should not generate any SQL
        await repo.update(1, 1)
        assert repo.db.committed is False

    @pytest.mark.asyncio
    async def test_get_by_id_with_no_items(self, repo):
        """Should handle collection with zero items."""
        repo.db._rows_by_query[("SELECT * FROM collections WHERE id = ? AND user_id = ?",
            (1, 1))] = [
            {"id": 1, "name": "Empty Collection"}
        ]
        repo.db._rows_by_query[("SELECT COUNT(*) as cnt FROM collection_items WHERE collection_id = ?",
            (1,))] = [{"cnt": 0}]
        
        collection = await repo.get_by_id(1, 1)
        assert collection["item_count"] == 0

    @pytest.mark.asyncio
    async def test_list_items_ordering(self, repo):
        """Should order items by created_at descending."""
        repo.db._rows_by_query[("SELECT * FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC",
            (1,))] = []
        await repo.list_items(1)
        executed = repo.db.executed_queries[-1]
        assert "ORDER BY created_at DESC" in executed[0]


class TestPublicCollections:
    """Test public collection operations."""

    @pytest.mark.asyncio
    async def test_create_public_collection(self, repo):
        """Should create a public collection."""
        collection_id = await repo.create(
            user_id=1,
            name="Public Collection",
            description="Shared with everyone",
            is_public=True,
        )
        assert collection_id is not None

    @pytest.mark.asyncio
    async def test_create_private_collection(self, repo):
        """Should create a private collection."""
        collection_id = await repo.create(
            user_id=1,
            name="Private Collection",
            description="My private items",
            is_public=False,
        )
        assert collection_id is not None

    @pytest.mark.asyncio
    async def test_update_public_status(self, repo):
        """Should update collection public/private status."""
        await repo.update(1, 1, is_public=True)
        assert repo.db.committed is True
        update_query = [q for q in repo.db.executed_queries if "UPDATE collections SET" in q[0]]
        assert "is_public = ?" in update_query[0][0]


class TestMultipleItems:
    """Test operations with multiple collection items."""

    @pytest.mark.asyncio
    async def test_add_multiple_items(self, repo):
        """Should add multiple items to collection."""
        item1 = await repo.add_item(1, document_id=1, search_result_id=None, note="First")
        item2 = await repo.add_item(1, document_id=2, search_result_id=None, note="Second")
        item3 = await repo.add_item(1, document_id=None, search_result_id=10, note="Third")
        assert item1 is not None
        assert item2 is not None
        assert item3 is not None
        assert len(repo.db.executed_queries) >= 3

    @pytest.mark.asyncio
    async def test_list_items_pagination(self, repo):
        """Should return all items in list."""
        repo.db._rows_by_query[("SELECT * FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC",
            (1,))] = [
            {"id": i, "document_id": i*10, "search_result_id": None, "note": f"Item {i}"}
            for i in range(1, 11)
        ]
        items = await repo.list_items(1)
        assert len(items) == 10
