
#This function
#Takes a query embedding (vector representation of a user question)
#Connects to PostgreSQL database (with pgvector)
#most similar text chunks from your PDFs
#Returns top k chunks as a list of strings

import psycopg2
from psycopg2.extras import RealDictCursor

def retrieve_similar_chunks(query_embedding, top_k=3):
    conn = psycopg2.connect(
        dbname="findora_db",
        user="findora",
        password="findorapass",
        host="localhost",
        port=5432
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT c.content
        FROM embeddings e
        JOIN chunks c ON e.chunk_id = c.id
        ORDER BY e.embedding <=> %s
        LIMIT %s;
        """,
        (query_embedding, top_k)
    )

    results = cur.fetchall()
    cur.close()
    conn.close()

    return [r["content"] for r in results]
