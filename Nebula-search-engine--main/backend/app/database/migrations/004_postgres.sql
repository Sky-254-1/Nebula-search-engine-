-- Nebula Search — PostgreSQL schema v1.3 (crawler tables)

CREATE TABLE IF NOT EXISTS crawler_jobs (
    id SERIAL PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    depth INTEGER NOT NULL DEFAULT 0,
    max_pages INTEGER NOT NULL DEFAULT 10,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawler_jobs_status ON crawler_jobs(status);
CREATE INDEX IF NOT EXISTS idx_crawler_jobs_created_at ON crawler_jobs(created_at);

CREATE TABLE IF NOT EXISTS crawled_pages (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES crawler_jobs(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    title VARCHAR(512),
    content TEXT,
    html TEXT,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawled_pages_job_id ON crawled_pages(job_id);
CREATE INDEX IF NOT EXISTS idx_crawled_pages_url ON crawled_pages(url);
