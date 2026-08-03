"""Behavioral tests for utils/pagination.py pure-logic functions."""
import pytest
from app.utils.pagination import (
    PaginatedResponse,
    paginate_query,
    paginate_cursor_query,
    create_pagination_response,
    create_cursor_pagination_response,
)


class TestPaginatedResponse:
    def test_to_dict_basic(self):
        resp = PaginatedResponse(
            items=[1, 2, 3], total=10, page=1, page_size=3,
            total_pages=4, has_next=True, has_previous=False,
        )
        d = resp.to_dict()
        assert d["items"] == [1, 2, 3]
        assert d["pagination"]["total"] == 10
        assert d["pagination"]["has_next"] is True

    def test_to_dict_with_cursors(self):
        resp = PaginatedResponse(
            items=[1], total=1, page=1, page_size=1,
            total_pages=1, has_next=False, has_previous=False,
            next_cursor="abc", previous_cursor="def",
        )
        d = resp.to_dict()
        assert "cursors" in d["pagination"]
        assert d["pagination"]["cursors"]["next"] == "abc"


class TestPaginateQuery:
    def test_basic_pagination(self):
        params = type("P", (), {"offset": 20, "limit": 10})()
        query, qparams = paginate_query("SELECT * FROM items", params)
        assert "LIMIT" in query
        assert "OFFSET" in query
        assert qparams == (20, 10)


class TestPaginateCursorQuery:
    def test_with_cursor(self):
        query, qparams = paginate_cursor_query("SELECT * FROM items", cursor="abc", limit=10)
        assert "WHERE" in query
        assert "ORDER BY" in query
        assert qparams == ("abc", 10)

    def test_without_cursor(self):
        query, qparams = paginate_cursor_query("SELECT * FROM items", cursor=None, limit=10)
        assert "ORDER BY" in query
        assert "WHERE" not in query
        assert qparams == (10,)


class TestCreatePaginationResponse:
    def test_basic(self):
        result = create_pagination_response(items=[1, 2, 3], total=10, page=1, page_size=3)
        assert result["items"] == [1, 2, 3]
        assert result["pagination"]["total"] == 10
        assert result["pagination"]["total_pages"] == 4
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_previous"] is False

    def test_last_page(self):
        result = create_pagination_response(items=[10], total=10, page=4, page_size=3)
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is True

    def test_single_page(self):
        result = create_pagination_response(items=[1], total=1, page=1, page_size=10)
        assert result["pagination"]["total_pages"] == 1
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_previous"] is False


class TestCreateCursorPaginationResponse:
    def test_with_items_and_next(self):
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = create_cursor_pagination_response(items, has_next=True)
        assert result["items"] == items
        assert result["pagination"]["has_next"] is True
        assert "cursors" in result["pagination"]

    def test_with_items_no_next(self):
        items = [{"id": 1}]
        result = create_cursor_pagination_response(items, has_next=False)
        assert result["pagination"]["has_next"] is False

    def test_empty_items(self):
        result = create_cursor_pagination_response([], has_next=False)
        assert result["items"] == []