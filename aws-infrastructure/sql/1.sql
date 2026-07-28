-- modules/database/sql/1.sql

-- 1. Create the evolution tracker table to manage schema states
CREATE TABLE IF NOT EXISTS schema_evolutions (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector; 

-- 3. Table for storing document pages
CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    source_path TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    UNIQUE(source_path, page_index)
);

-- 4. Table for storing vector embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    vector vector(384) NOT NULL, 
    text TEXT NOT NULL,
    body TEXT NOT NULL,
    source_path TEXT NOT NULL,
    page_index INTEGER NOT NULL,
    token_offset INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    section_path TEXT,
    section_index INTEGER,
    section_total INTEGER
);

-- 5. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pages_text_gin ON pages USING gin (raw_text gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_embeddings_source ON embeddings(source_path);
CREATE INDEX IF NOT EXISTS idx_pages_source ON pages(source_path);
