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

def build_prompt(context_chunks: list[str], chat_history: list[str], question: str, web_results: list[str] = None):
    # Prepare Document Context
    doc_context = "\n\n".join(context_chunks) if context_chunks else ""
    
    # Prepare Web Context
    web_context = ""
    if web_results:
        web_context = "\n\n".join(web_results)
    
    history = "\n".join(chat_history)
    
    prompt = f"""
You are Findora AI, a helpful and expert assistant.
Your goal is to provide accurate, comprehensive, and detailed answers using the provided Context sources.

Instructions:
1. Prioritize "Document Context" if it contains the specific answer.
2. If "Document Context" is missing or irrelevant, use "Web Search Context" to provide a thorough and detailed explanation.
3. If the user asks for real-time data or definitions, provide a complete response with all relevant details found in the snippets.
4. Do NOT start your response by explaining what is NOT in the documents. Just provide the best and most complete answer available.
5. If using information from the internet, briefly mention "(Source: Web)" at the end of your answer.
6. Maintain a helpful and professional tone, providing as much relevant information as the context allows.

Chat History:
{history}

Document Context:
{doc_context if doc_context else "None available."}

Web Search Context:
{web_context if web_context else "None available."}

Question:
{question}

Answer:
"""
    # print(f"[DEBUG] Full Prompt: {prompt}")
    return prompt