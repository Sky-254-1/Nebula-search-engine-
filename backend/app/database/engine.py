"""Database engine with SQLite and PostgreSQL support."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

import aiosqlite

from app.config import get_settings

settings = get_settings()


def _adapt_sql(sql: str) -> str:
    """Convert SQLite-style placeholders to PostgreSQL $1, $2, ..."""
    index = 0

    def repl(_match: re.Match) -> str:
        nonlocal index
        index += 1
        return f"${index}"

    return re.sub(r"\?", repl, sql)


class DatabaseConnection(ABC):
    @abstractmethod
    async def execute(self, sql: str, params: tuple = ()) -> Any:
        pass

    @abstractmethod
    async def fetchone(self, sql: str, params: tuple = ()) -> Any:
        pass

    @abstractmethod
    async def fetchall(self, sql: str, params: tuple = ()) -> list[Any]:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class SQLiteConnection(DatabaseConnection):
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    async def execute(self, sql: str, params: tuple = ()) -> Any:
        return await self._conn.execute(sql, params)

    async def fetchone(self, sql: str, params: tuple = ()) -> Any:
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()) -> list[Any]:
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchall()

    async def commit(self) -> None:
        await self._conn.commit()

    async def close(self) -> None:
        await self._conn.close()


class PostgresConnection(DatabaseConnection):
    def __init__(self, conn):
        self._conn = conn

    async def execute(self, sql: str, params: tuple = ()) -> Any:
        return await self._conn.execute(_adapt_sql(sql), *params)

    async def fetchone(self, sql: str, params: tuple = ()) -> Any:
        row = await self._conn.fetchrow(_adapt_sql(sql), *params)
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple = ()) -> list[Any]:
        rows = await self._conn.fetch(_adapt_sql(sql), *params)
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        await self._conn.close()


async def connect() -> DatabaseConnection:
    if settings.uses_postgres:
        import asyncpg

        url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url)
        return PostgresConnection(conn)
    conn = await aiosqlite.connect(settings.db_path)
    conn.row_factory = aiosqlite.Row
    return SQLiteConnection(conn)
