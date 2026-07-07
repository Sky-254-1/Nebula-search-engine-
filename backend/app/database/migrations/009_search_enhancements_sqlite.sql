-- Migration 009: Search enhancements (saved searches, search suggestions) - SQLite-safe

CREATE TABLE IF NOT EXISTS saved_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    mode TEXT DEFAULT 'hybrid' NOT NULL,
    filters TEXT DEFAULT '{}',
    is_alert INTEGER DEFAULT 0 NOT NULL,
    last_alerted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER DEFAULT 0 NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_searches_user_query ON saved_searches(user_id, query) WHERE is_deleted = 0;

-- Search suggestions aggregation table
CREATE TABLE IF NOT EXISTS search_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_normalized TEXT NOT NULL,
    search_count INTEGER DEFAULT 1 NOT NULL,
    last_searched_at TEXT NOT NULL DEFAULT (datetime('now')),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER DEFAULT 0 NOT NULL,
    deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_query ON search_suggestions(query_normalized);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_count ON search_suggestions(search_count DESC);
CREATE INDEX IF NOT EXISTS idx_search_suggestions_user ON search_suggestions(user_id) WHERE is_deleted = 0 AND user_id IS NOT NULL;
