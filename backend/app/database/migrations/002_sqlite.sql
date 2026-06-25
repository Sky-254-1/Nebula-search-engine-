-- Nebula Search — SQLite schema v1.1 (vector indexing)

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0,
    content_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_user_id ON chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON chunks(content_hash);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    model TEXT NOT NULL DEFAULT 'local-hash',
    dimensions INTEGER NOT NULL DEFAULT 256,
    vector_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id);

CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    document_id INTEGER,
    chunk_id INTEGER,
    query TEXT NOT NULL,
    snippet TEXT,
    score REAL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_citations_user_id ON citations(user_id);
CREATE INDEX IF NOT EXISTS idx_citations_document_id ON citations(document_id);

CREATE TABLE IF NOT EXISTS search_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'hybrid',
    results_count INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_search_sessions_user_id ON search_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_started_at ON search_sessions(started_at);

-- SQLite lacks IF NOT EXISTS for ALTER COLUMN; ignore errors on re-run via migrate skip logic
ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN content_hash TEXT;
ALTER TABLE documents ADD COLUMN error_message TEXT;
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
