"""Database engine with SQLite and PostgreSQL support, including connection pooling."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

import aiosqlite

from app.config import get_settings

settings = get_settings()

# Global connection pool for PostgreSQL
_postgres_pool = None


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
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple = ()) -> list[Any]:
        cursor = await self._conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

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


class PostgresPooledConnection(DatabaseConnection):
    """Connection pool wrapper for PostgreSQL."""
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
        # Return connection to pool instead of closing
        pass


async def init_pool() -> None:
    """Initialize PostgreSQL connection pool."""
    global _postgres_pool
    if not settings.uses_postgres:
        return
    try:
        import asyncpg
        url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _postgres_pool = await asyncpg.create_pool(
            url,
            min_size=5,
            max_size=20,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
        )
    except Exception:
        _postgres_pool = None


async def get_pooled_connection() -> DatabaseConnection:
    """Get a connection from the pool."""
    if not _postgres_pool:
        # Fallback to direct connection if pool not initialized
        return await connect()
    conn = await _postgres_pool.acquire()
    return PostgresPooledConnection(conn)


async def close_pool() -> None:
    """Close the connection pool."""
    global _postgres_pool
    if _postgres_pool:
        await _postgres_pool.close()
        _postgres_pool = None


async def connect() -> DatabaseConnection:
    if settings.uses_postgres:
        # Try to use pool if available
        if _postgres_pool:
            return await get_pooled_connection()
        # Fallback to direct connection
        import asyncpg
        url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(url)
        return PostgresConnection(conn)
    conn = await aiosqlite.connect(settings.db_path)
    conn.row_factory = aiosqlite.Row
    return SQLiteConnection(conn)
