from app.embedding import embed
from app.database import get_conn

def retrieve_chunks(query: str, top_k=5):
    q_emb = embed([query])[0]
    sql = """
    SELECT content
    FROM chunks
    ORDER BY embedding <-> %s
    LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (q_emb, top_k))
            return [r["content"] for r in cur.fetchall()]

def build_prompt(context_chunks: list[str], chat_history: list[str], question: str):
    context = "\n\n".join(context_chunks)
    history = "\n".join(chat_history)
    return f"""
Use the context below to answer the question.
If the answer is not in the context, say "I don't know".

Chat History:
{history}

Context:
{context}

Question:
{question}

Answer:
"""
