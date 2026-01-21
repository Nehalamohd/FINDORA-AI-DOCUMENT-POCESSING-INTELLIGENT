from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Findora AI")

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="findora_db",
        user="findora",
        password="findorapass"
    )

class Query(BaseModel):
    embedding: list[float]
    top_k: int = 3

@app.post("/search")
def search(query: Query):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT c.content
        FROM embeddings e
        JOIN chunks c ON e.chunk_id = c.id
        ORDER BY e.embedding <=> %s
        LIMIT %s;
        """,
        (query.embedding, query.top_k)
    )

    results = cur.fetchall()
    cur.close()
    conn.close()

    return {"results": [r["content"] for r in results]}
