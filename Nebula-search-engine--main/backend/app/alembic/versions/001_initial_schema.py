"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = "001"
down_revision = None


def _is_pg():
    return op.get_context().dialect.name == "postgresql"


def _table_exists(name):
    conn = op.get_bind()
    if _is_pg():
        result = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"
            ),
            {"t": name},
        ).scalar()
        return bool(result)
    result = conn.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:t"
        ),
        {"t": name},
    ).fetchone()
    return result is not None


def _index_exists(name):
    conn = op.get_bind()
    if _is_pg():
        result = conn.execute(
            text("SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :n)"),
            {"n": name},
        ).scalar()
        return bool(result)
    result = conn.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=:n"
        ),
        {"n": name},
    ).fetchone()
    return result is not None


def _ct(name, *columns):
    if not _table_exists(name):
        op.create_table(name, *columns)


def _ci(name, table, columns, **kwargs):
    if not _index_exists(name):
        op.create_index(name, table, columns, **kwargs)


def upgrade():
    is_pg = _is_pg()

    # --- users ---
    _ct(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role", sa.String(50), nullable=False, server_default=sa.text("'user'")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_users_email", "users", ["email"], unique=True)
    _ci("ix_users_created_at", "users", ["created_at"])

    # --- sessions ---
    _ct(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(255), nullable=True),
        sa.Column("parent_refresh_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    _ci("ix_sessions_session_id", "sessions", ["session_id"])
    _ci("ix_sessions_user_id", "sessions", ["user_id"])
    _ci("ix_sessions_expires_at", "sessions", ["expires_at"])
    _ci("ix_sessions_created_at", "sessions", ["created_at"])

    # --- queries ---
    _ct(
        "queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("backend", sa.String(50), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_queries_user_id", "queries", ["user_id"])
    _ci("ix_queries_created_at", "queries", ["created_at"])

    # --- documents ---
    _ct(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_documents_user_id", "documents", ["user_id"])
    _ci("ix_documents_status", "documents", ["status"])
    _ci("ix_documents_created_at", "documents", ["created_at"])

    # --- chunks ---
    _ct(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_chunks_document_id", "chunks", ["document_id"])
    _ci("ix_chunks_created_at", "chunks", ["created_at"])

    # --- embeddings ---
    if is_pg:
        op.execute(
            text(
                "CREATE TABLE IF NOT EXISTS embeddings ("
                "  id SERIAL PRIMARY KEY,"
                "  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,"
                "  chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,"
                "  embedding vector(1536),"
                "  model_name VARCHAR(255) NOT NULL,"
                "  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
    else:
        _ct(
            "embeddings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "document_id",
                sa.Integer(),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "chunk_id",
                sa.Integer(),
                sa.ForeignKey("chunks.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("embedding", sa.Text(), nullable=True),
            sa.Column("model_name", sa.String(255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP"),
            ),
        )
    if not _index_exists("ix_embeddings_document_id"):
        op.create_index("ix_embeddings_document_id", "embeddings", ["document_id"])
    if not _index_exists("ix_embeddings_chunk_id"):
        op.create_index("ix_embeddings_chunk_id", "embeddings", ["chunk_id"])
    if not _index_exists("ix_embeddings_created_at"):
        op.create_index("ix_embeddings_created_at", "embeddings", ["created_at"])

    # --- search_results ---
    _ct(
        "search_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "query_id",
            sa.Integer(),
            sa.ForeignKey("queries.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_search_results_user_id", "search_results", ["user_id"])
    _ci("ix_search_results_query_id", "search_results", ["query_id"])
    _ci("ix_search_results_created_at", "search_results", ["created_at"])

    # --- notifications ---
    _ct(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_notifications_user_id", "notifications", ["user_id"])
    _ci("ix_notifications_created_at", "notifications", ["created_at"])

    # --- analytics_events ---
    jsonb = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    _ct(
        "analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_data", jsonb, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_analytics_events_user_id", "analytics_events", ["user_id"])
    _ci("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    _ci("ix_analytics_events_created_at", "analytics_events", ["created_at"])

    # --- billing_plans ---
    _ct(
        "billing_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("features", jsonb, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_billing_plans_created_at", "billing_plans", ["created_at"])

    # --- billing_subscriptions ---
    _ct(
        "billing_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("billing_plans.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("current_period_start", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_billing_subscriptions_user_id", "billing_subscriptions", ["user_id"])
    _ci("ix_billing_subscriptions_plan_id", "billing_subscriptions", ["plan_id"])
    _ci("ix_billing_subscriptions_created_at", "billing_subscriptions", ["created_at"])

    # --- user_settings ---
    _ct(
        "user_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("settings", jsonb, nullable=True, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_user_settings_user_id", "user_settings", ["user_id"])

    # --- audit_logs ---
    _ct(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", jsonb, nullable=True, server_default=sa.text("'{}'")),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    _ci("ix_audit_logs_action", "audit_logs", ["action"])
    _ci("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # --- saved_searches ---
    _ct(
        "saved_searches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters", jsonb, nullable=True, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_saved_searches_user_id", "saved_searches", ["user_id"])
    _ci("ix_saved_searches_created_at", "saved_searches", ["created_at"])

    # --- collections ---
    _ct(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_collections_user_id", "collections", ["user_id"])
    _ci("ix_collections_created_at", "collections", ["created_at"])

    # --- collection_items ---
    _ct(
        "collection_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("search_result_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_collection_items_collection_id", "collection_items", ["collection_id"])
    _ci("ix_collection_items_document_id", "collection_items", ["document_id"])
    _ci("ix_collection_items_created_at", "collection_items", ["created_at"])

    # --- bookmarks ---
    _ct(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_bookmarks_user_id", "bookmarks", ["user_id"])
    _ci("ix_bookmarks_created_at", "bookmarks", ["created_at"])

    # --- chat_messages ---
    _ct(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    _ci("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    # --- crawler_jobs ---
    _ct(
        "crawler_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("depth", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_crawler_jobs_status", "crawler_jobs", ["status"])
    _ci("ix_crawler_jobs_created_at", "crawler_jobs", ["created_at"])

    # --- crawled_pages ---
    _ct(
        "crawled_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("crawler_jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("html", sa.Text(), nullable=True),
        sa.Column(
            "extracted_at",
            sa.DateTime(),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    _ci("ix_crawled_pages_job_id", "crawled_pages", ["job_id"])
    _ci("ix_crawled_pages_extracted_at", "crawled_pages", ["extracted_at"])

    # --- PostgreSQL-specific indexes ---
    if is_pg:
        # GIN index on queries.query for full-text search
        if not _index_exists("ix_queries_query_gin"):
            op.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_queries_query_gin "
                    "ON queries USING gin (to_tsvector('english', query))"
                )
            )

        # ivfflat index on embeddings.embedding for vector similarity search
        if not _index_exists("ix_embeddings_embedding_ivfflat"):
            op.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_embeddings_embedding_ivfflat "
                    "ON embeddings USING ivfflat (embedding vector_cosine_ops) "
                    "WITH (lists = 100)"
                )
            )


def downgrade():
    tables = [
        "crawled_pages",
        "crawler_jobs",
        "chat_messages",
        "bookmarks",
        "collection_items",
        "collections",
        "saved_searches",
        "audit_logs",
        "user_settings",
        "billing_subscriptions",
        "billing_plans",
        "analytics_events",
        "notifications",
        "search_results",
        "embeddings",
        "chunks",
        "documents",
        "queries",
        "sessions",
        "users",
    ]
    for table in tables:
        if _is_pg():
            op.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        else:
            op.execute(text(f"DROP TABLE IF EXISTS {table}"))
