"""Behavioral tests for utils/filtering.py pure-logic functions."""
import pytest
from app.utils.filtering import (
    FilterOperator,
    FilterCondition,
    SortCondition,
    FilterSet,
    SortSet,
    parse_filter_params,
    parse_sort_params,
)


class TestFilterCondition:
    def test_eq_to_sql(self):
        cond = FilterCondition("status", FilterOperator.EQ, "active")
        sql, params = cond.to_sql(0)
        assert sql == "status = ?"
        assert params == ("active",)

    def test_gt_to_sql(self):
        cond = FilterCondition("age", FilterOperator.GT, 18)
        sql, params = cond.to_sql(0)
        assert sql == "age > ?"
        assert params == (18,)

    def test_in_to_sql(self):
        cond = FilterCondition("id", FilterOperator.IN, [1, 2, 3])
        sql, params = cond.to_sql(0)
        assert "IN" in sql
        assert params == (1, 2, 3)

    def test_between_to_sql(self):
        cond = FilterCondition("date", FilterOperator.BETWEEN, "2024-01-01", "2024-12-31")
        sql, params = cond.to_sql(0)
        assert "BETWEEN" in sql
        assert params == ("2024-01-01", "2024-12-31")

    def test_is_null_to_sql(self):
        cond = FilterCondition("deleted", FilterOperator.IS_NULL, None)
        sql, params = cond.to_sql(0)
        assert "IS NULL" in sql
        assert params == ()

    def test_is_not_null_to_sql(self):
        cond = FilterCondition("deleted", FilterOperator.IS_NOT_NULL, None)
        sql, params = cond.to_sql(0)
        assert "IS NOT NULL" in sql
        assert params == ()

    def test_like_to_sql(self):
        cond = FilterCondition("name", FilterOperator.LIKE, "%test%")
        sql, params = cond.to_sql(0)
        assert "LIKE" in sql
        assert params == ("%test%",)

    def test_invalid_field_name(self):
        cond = FilterCondition("field; DROP TABLE", FilterOperator.EQ, "x")
        with pytest.raises(ValueError):
            cond.to_sql(0)


class TestSortCondition:
    def test_asc(self):
        sort = SortCondition("name", "asc")
        assert sort.to_sql() == "name ASC"

    def test_desc(self):
        sort = SortCondition("name", "desc")
        assert sort.to_sql() == "name DESC"

    def test_invalid_field(self):
        sort = SortCondition("name; DROP", "asc")
        with pytest.raises(ValueError):
            sort.to_sql()


class TestFilterSet:
    def test_empty(self):
        fs = FilterSet()
        sql, params = fs.to_sql()
        assert sql == ""
        assert params == ()

    def test_multiple_filters(self):
        fs = FilterSet().eq("status", "active").gt("age", 18)
        sql, params = fs.to_sql()
        assert "WHERE" in sql
        assert "AND" in sql
        assert params == ("active", 18)

    def test_chaining(self):
        fs = FilterSet()
        assert fs.eq("a", 1) is fs
        assert fs.ne("b", 2) is fs


class TestSortSet:
    def test_empty(self):
        ss = SortSet()
        assert ss.to_sql() == ""

    def test_multiple_sorts(self):
        ss = SortSet().asc("name").desc("date")
        sql = ss.to_sql()
        assert "ORDER BY" in sql
        assert "ASC" in sql
        assert "DESC" in sql

    def test_allowed_fields(self):
        ss = SortSet()
        ss.set_allowed_fields(["name", "date"])
        ss.asc("name")
        with pytest.raises(ValueError):
            ss.desc("invalid_field")


class TestParseFilterParams:
    def test_empty(self):
        fs = parse_filter_params(None)
        assert len(fs.filters) == 0

    def test_single_filter(self):
        fs = parse_filter_params("status:eq:active")
        assert len(fs.filters) == 1

    def test_multiple_filters(self):
        fs = parse_filter_params("status:eq:active,age:gt:18")
        assert len(fs.filters) == 2

    def test_in_operator(self):
        fs = parse_filter_params("id:in:1|2|3")
        assert len(fs.filters) == 1
        assert fs.filters[0].value == ["1", "2", "3"]

    def test_between_operator(self):
        fs = parse_filter_params("date:between:2024-01-01|2024-12-31")
        assert len(fs.filters) == 1
        assert fs.filters[0].value == "2024-01-01"
        assert fs.filters[0].value2 == "2024-12-31"

    def test_invalid_format(self):
        fs = parse_filter_params("invalid")
        assert len(fs.filters) == 0

    def test_allowed_fields(self):
        fs = parse_filter_params("status:eq:active", allowed_fields=["name"])
        assert len(fs.filters) == 0

    def test_invalid_operator(self):
        fs = parse_filter_params("status:invalid:active")
        assert len(fs.filters) == 0


class TestParseSortParams:
    def test_empty(self):
        ss = parse_sort_params(None)
        assert len(ss.sorts) == 1  # Default sort

    def test_single_sort(self):
        ss = parse_sort_params("name:desc")
        assert len(ss.sorts) == 1
        assert ss.sorts[0].field == "name"
        assert ss.sorts[0].direction == "desc"

    def test_multiple_sorts(self):
        ss = parse_sort_params("name:asc,date:desc")
        assert len(ss.sorts) == 2

    def test_invalid_format(self):
        ss = parse_sort_params("invalid")
        assert len(ss.sorts) == 0

    def test_invalid_direction(self):
        ss = parse_sort_params("name:invalid")
        assert len(ss.sorts) == 0

    def test_allowed_fields(self):
        ss = parse_sort_params("name:asc", allowed_fields=["date"])
        assert len(ss.sorts) == 0