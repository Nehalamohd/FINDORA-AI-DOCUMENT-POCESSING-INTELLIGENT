#PUTTING DATA into the database
#Text  →  Embedding  →  Store in PostgreSQL (pgvector)


import psycopg2
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Generate embedding
text = "This is a test chunk stored in database"
embedding = model.encode(text).tolist()

# Connect DB
conn = psycopg2.connect(
    dbname="findora_db",
    user="findora",
    password="findorapass",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# Insert document
cur.execute(
    "INSERT INTO documents (filename) VALUES (%s) RETURNING id;",
    ("test.pdf",)
)
document_id = cur.fetchone()[0]

# Insert chunk
cur.execute(
    "INSERT INTO chunks (document_id, content) VALUES (%s, %s) RETURNING id;",
    (document_id, text)
)
chunk_id = cur.fetchone()[0]

# Insert embedding
cur.execute(
    "INSERT INTO embeddings (chunk_id, embedding) VALUES (%s, %s);",
    (chunk_id, embedding)
)

conn.commit()
cur.close()
conn.close()

print("Inserted document, chunk, and embedding successfully")
