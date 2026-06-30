CREATE TABLE IF NOT EXISTS search_clicks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    search_log_id INTEGER REFERENCES search_logs(id) ON DELETE SET NULL,
    query VARCHAR(500) NOT NULL,
    result_url VARCHAR(2000) NOT NULL,
    result_title VARCHAR(500),
    result_position INTEGER,
    backend VARCHAR(50),
    clicked_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_search_clicks_user_id ON search_clicks(user_id);
CREATE INDEX IF NOT EXISTS idx_search_clicks_query ON search_clicks(query);
