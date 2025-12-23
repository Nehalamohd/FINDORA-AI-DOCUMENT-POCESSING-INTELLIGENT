import psycopg2
from app.config import DB_CONFIG

def update_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Checking database schema...")
    
    # 0. Create 'users' table
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'users';")
    if not cur.fetchone():
        print("Creating 'users' table...")
        cur.execute("""
            CREATE TABLE users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    # 1. Create 'flows' table
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'flows';")
    if not cur.fetchone():
        print("Creating 'flows' table...")
        cur.execute("""
            CREATE TABLE flows (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        # Add user_id to flows if it doesn't exist
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'flows';")
        flow_cols = [c[0] for c in cur.fetchall()]
        if 'user_id' not in flow_cols:
            print("Adding 'user_id' to 'flows'...")
            cur.execute("ALTER TABLE flows ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;")

    # 1. Update 'documents' table
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'documents';")
    existing_cols = [c[0] for c in cur.fetchall()]
    
    if 'status' not in existing_cols:
        print("Adding missing columns to 'documents' table...")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending';")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS task_id TEXT;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size INTEGER;")
        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS flow_id UUID REFERENCES flows(id) ON DELETE CASCADE;")
    
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'sessions';")
    if not cur.fetchone():
        print("Creating 'sessions' table...")
        cur.execute("CREATE TABLE sessions (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), flow_id UUID REFERENCES flows(id) ON DELETE CASCADE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
    else:
        # Check for flow_id in sessions
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sessions';")
        session_cols = [c[0] for c in cur.fetchall()]
        if 'flow_id' not in session_cols:
            print("Adding 'flow_id' to 'sessions'...")
            cur.execute("ALTER TABLE sessions ADD COLUMN flow_id UUID REFERENCES flows(id) ON DELETE CASCADE;")

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'messages';")
    if not cur.fetchone():
        print("Creating 'messages' table...")
        cur.execute("CREATE TABLE messages (id SERIAL PRIMARY KEY, session_id UUID REFERENCES sessions(id) ON DELETE CASCADE, role TEXT CHECK (role IN ('user','assistant')), content TEXT, retrieved_context JSONB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")

    # 2. Update 'chunks' table for Hybrid Search
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'chunks';")
    existing_chunks_cols = [c[0] for c in cur.fetchall()]
    
    if 'tsv' not in existing_chunks_cols:
        print("Adding 'tsv' column to 'chunks' table for Hybrid Search...")
        cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS tsv tsvector;")
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN(tsv);")
        
        # Add trigger
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

    conn.commit()
    cur.close()
    conn.close()
    print("Database schema update complete!")

if __name__ == "__main__":
    update_database()
