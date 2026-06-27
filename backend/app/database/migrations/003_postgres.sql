-- Nebula Search — PostgreSQL schema v1.2 (Security & RBAC)

-- Add role to users
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';

-- Add details to sessions
ALTER TABLE sessions ADD COLUMN session_id TEXT;
ALTER TABLE sessions ADD COLUMN device_name TEXT;
ALTER TABLE sessions ADD COLUMN last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE sessions ADD COLUMN parent_refresh_id INTEGER;
ALTER TABLE sessions ADD COLUMN rotated_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE sessions ADD COLUMN revoked_reason TEXT;

CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_parent_refresh_id ON sessions(parent_refresh_id);

-- Create audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    resource TEXT,
    metadata_json TEXT DEFAULT '{}',
    ip TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
