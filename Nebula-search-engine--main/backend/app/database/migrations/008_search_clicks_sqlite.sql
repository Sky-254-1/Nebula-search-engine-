CREATE TABLE IF NOT EXISTS search_clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    search_log_id INTEGER REFERENCES search_logs(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    result_url TEXT NOT NULL,
    result_title TEXT,
    result_position INTEGER,
    backend TEXT,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_search_clicks_user_id ON search_clicks(user_id);
CREATE INDEX IF NOT EXISTS idx_search_clicks_query ON search_clicks(query);
