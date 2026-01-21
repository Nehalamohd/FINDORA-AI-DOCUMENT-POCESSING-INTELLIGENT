-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Flows table
CREATE TABLE IF NOT EXISTS flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    flow_id UUID REFERENCES flows(id) ON DELETE CASCADE, 
    filename TEXT,
    file_path TEXT,
    file_type TEXT,
    file_size INTEGER,
    total_pages INTEGER,
    status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
    task_id TEXT,
    error_message TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pages table
CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    content TEXT
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    content TEXT,
    tsv tsvector
);

-- Index for full-text search
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN(tsv);

-- Update trigger for tsvector
CREATE OR REPLACE FUNCTION chunks_trigger() RETURNS trigger AS $$
begin
  new.tsv := to_tsvector('english', coalesce(new.content, ''));
  return new;
end
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvupdate BEFORE INSERT OR UPDATE
ON chunks FOR EACH ROW EXECUTE FUNCTION chunks_trigger();

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
    embedding VECTOR(384)
);

-- Index for fast vector search
CREATE INDEX IF NOT EXISTS embeddings_vector_idx
ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID REFERENCES flows(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user','assistant')),
    content TEXT,
    retrieved_context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
