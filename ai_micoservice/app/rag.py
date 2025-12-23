from app.embedding import embed
from app.database import get_conn

def retrieve_chunks(query: str, top_k=5, flow_id: str = None):
    """
    Hybrid Search: Semantic (pgvector) + Keyword (BM25/FTS)
    Uses a simple weighted score.
    """
    q_emb = embed([query])[0]
    
    # SQL for Hybrid Search using Postgres Full Text Search and pgvector
    # Join with documents to filter by flow_id
    sql = """
    WITH semantic_search AS (
        SELECT e.chunk_id, 1 - (e.embedding <=> %s::vector) AS score
        FROM embeddings e
        JOIN chunks c ON e.chunk_id = c.id
        JOIN documents d ON c.document_id = d.id
        WHERE d.flow_id = %s::uuid OR %s::uuid IS NULL
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    ),
    keyword_search AS (
        SELECT c.id as chunk_id, ts_rank_cd(c.tsv, plainto_tsquery('english', %s)) AS score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (c.tsv @@ plainto_tsquery('english', %s)) 
          AND (d.flow_id = %s::uuid OR %s::uuid IS NULL)
        ORDER BY score DESC
        LIMIT %s
    )
    SELECT c.content, 
           COALESCE(s.score, 0) * 0.7 + COALESCE(k.score, 0) * 0.3 AS hybrid_score
    FROM chunks c
    LEFT JOIN semantic_search s ON c.id = s.chunk_id
    LEFT JOIN keyword_search k ON c.id = k.chunk_id
    WHERE s.chunk_id IS NOT NULL OR k.chunk_id IS NOT NULL
    ORDER BY hybrid_score DESC
    LIMIT %s;
    """
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # We pass flow_id multiple times for the OR logic
            params = (
                q_emb, flow_id, flow_id, q_emb, top_k * 2, # semantic
                query, query, flow_id, flow_id, top_k * 2, # keyword
                top_k # final limit
            )
            cur.execute(sql, params)
            results = cur.fetchall()
            return [r["content"] for r in results]

def build_prompt(context_chunks: list[str], chat_history: list[str], question: str):
    context = "\n\n".join(context_chunks)
    history = "\n".join(chat_history)
    return f"""
You are Findora AI, a helpful and expert assistant. Your goal is to provide comprehensive and insightful answers based on the provided document context.

Instructions:
1. Use the provided "Context" to answer the user's "Question".
2. If the answer isn't directly stated but can be inferred or summarized from the context, please provide a thoughtful summary.
3. Keep the tone professional yet conversational.
4. If the context is completely irrelevant to the question, gracefully explain that the document doesn't seem to cover that specific topic, but offer to explain what the document *is* about based on the available information.

Chat History:
{history}

Context:
{context}

Question:
{question}

Answer:
"""
