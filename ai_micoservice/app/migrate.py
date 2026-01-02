import psycopg2
from app.config import DB_CONFIG

def update_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Checking database schema...")
    
    # 0. Create 'users' table
    print("Ensuring 'users' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 1. Create 'flows' table
    print("Ensuring 'flows' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flows (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 1.1 Ensure 'documents' table
    print("Ensuring 'documents' table...")
    cur.execute("""
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
    """)

    # 1.2 Update 'documents' columns if needed (backward compatibility)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'documents';")
    existing_cols = [c[0] for c in cur.fetchall()]
    if 'status' not in existing_cols:
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending';")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS task_id TEXT;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size INTEGER;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS flow_id UUID REFERENCES flows(id) ON DELETE CASCADE;")

    # 2. Sessions
    print("Ensuring 'sessions' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
            flow_id UUID REFERENCES flows(id) ON DELETE CASCADE, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Messages
    print("Ensuring 'messages' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY, 
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE, 
            role TEXT CHECK (role IN ('user','assistant')), 
            content TEXT, 
            retrieved_context JSONB, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 4. Pages and Chunks (Basic structures)
    print("Ensuring 'pages' and 'chunks' tables...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            page_number INTEGER,
            content TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            page_id INTEGER REFERENCES pages(id) ON DELETE CASCADE,
            chunk_index INTEGER,
            content TEXT,
            tsv tsvector
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN(tsv);")
    
    # 5. Embeddings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            chunk_id INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
            embedding VECTOR(384)
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS embeddings_vector_idx
        ON embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # 6. TSVector Trigger
    cur.execute("""
    CREATE OR REPLACE FUNCTION chunks_trigger() RETURNS trigger AS $$
    begin
      new.tsv := to_tsvector('english', coalesce(new.content, ''));
      return new;
    end
    $$ LANGUAGE plpgsql;
    """)
    cur.execute("DROP TRIGGER IF EXISTS tsvupdate ON chunks;")
    cur.execute("CREATE TRIGGER tsvupdate BEFORE INSERT OR UPDATE ON chunks FOR EACH ROW EXECUTE FUNCTION chunks_trigger();")

    # 7. Golden Dataset
    print("Ensuring 'golden_qa' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS golden_qa (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            flow_id UUID REFERENCES flows(id) ON DELETE CASCADE,
            question TEXT NOT NULL,
            expected_answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 8. Evaluations
    print("Ensuring 'evaluations' table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            golden_id UUID REFERENCES golden_qa(id) ON DELETE CASCADE,
            generated_answer TEXT,
            similarity_score FLOAT, 
            judge_feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Database schema update complete!")

if __name__ == "__main__":
    update_database()
