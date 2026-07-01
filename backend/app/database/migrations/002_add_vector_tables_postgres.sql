-- Migration 002: Add vector search tables (PostgreSQL)
-- Version: 1.1.0
-- Date: 2026-07-01
-- Description: Adds document_chunks, embeddings, citations, search_sessions tables for vector search

-- Document Chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON document_chunks(chunk_index);

-- Embeddings (for vector similarity search)
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    vector TEXT NOT NULL,  -- JSON array of floats
    model_name TEXT NOT NULL DEFAULT 'stub',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_id ON embeddings(chunk_id);

-- Citations (track which chunks were used in answers)
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    document_id INTEGER,
    chunk_id INTEGER,
    snippet TEXT,
    score REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_citations_user_id ON citations(user_id);
CREATE INDEX IF NOT EXISTS idx_citations_query ON citations(query);
CREATE INDEX IF NOT EXISTS idx_citations_document_id ON citations(document_id);

-- Search sessions (for session tracking in search)
CREATE TABLE IF NOT EXISTS search_sessions (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ,
    query_count INTEGER DEFAULT 0,
    last_query_at TIMESTAMPTZ,
    metadata_json JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_search_sessions_session_id ON search_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_user_id ON search_sessions(user_id);

-- Document table updates
ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
