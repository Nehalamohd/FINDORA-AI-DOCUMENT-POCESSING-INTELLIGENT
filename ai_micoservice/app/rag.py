from app.embedding import embed
from app.database import SessionLocal
from sqlalchemy import text

def retrieve_chunks(query: str, top_k=5, flow_id: str = None):
    """
    Hybrid Search: Semantic (pgvector) + Keyword (BM25/FTS)
    Uses a simple weighted score.
    """
    q_emb = embed([query])[0]
    
    #create temp table for semantic and keyword search
    #chunk id tells which chunk matches the query
    #%s::vector is query embedding
    #cosine_similarity = 1 - cosine_distance
    #similarity score btwn 0 ,1.... 0 identical
    #every embeddings belongs to chunk... evry chunk blngs to doc
    #evry  doc blng to flow
    #flowid null search every where... else search inside the flow
    #keep only top k res
    # ts_rank_cd() = ranking function for full text search
    #Higher score = better keyword match
    #c.tsv is the tsvector column in chunks table
    #plainto_tsquery converts user query to searchable tokens
    #@@ matches text against tsvector
    # final select combines both results
    sql = """
    WITH semantic_search AS (
        SELECT e.chunk_id, 1 - (e.embedding <=> CAST(:q_emb AS vector)) AS score
        FROM embeddings e
        JOIN chunks c ON e.chunk_id = c.id
        JOIN documents d ON c.document_id = d.id
        WHERE d.flow_id = CAST(:flow_id AS uuid) OR :flow_id IS NULL
        ORDER BY e.embedding <=> CAST(:q_emb AS vector)
        LIMIT :top_k_2
    ),
    
    keyword_search AS (
        SELECT c.id as chunk_id, ts_rank_cd(c.tsv, plainto_tsquery('english', :query)) AS score
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE (c.tsv @@ plainto_tsquery('english', :query)) 
          AND (d.flow_id = CAST(:flow_id AS uuid) OR :flow_id IS NULL)
        ORDER BY score DESC
        LIMIT :top_k_2
    )

    SELECT c.content, 
           COALESCE(s.score, 0) * 0.7 + COALESCE(k.score, 0) * 0.3 AS hybrid_score
    FROM chunks c
    LEFT JOIN semantic_search s ON c.id = s.chunk_id
    LEFT JOIN keyword_search k ON c.id = k.chunk_id
    WHERE s.chunk_id IS NOT NULL OR k.chunk_id IS NOT NULL
    ORDER BY hybrid_score DESC
    LIMIT :top_k;
    """
    
    db = SessionLocal()
    try:
        params = {
            "q_emb": str(q_emb.tolist()) if hasattr(q_emb, 'tolist') else str(q_emb),
            "flow_id": flow_id,
            "query": query,
            "top_k_2": top_k * 2,
            "top_k": top_k
        }
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        return [r[0] for r in rows] # Returns final best chunks to your app
    finally:
        db.close()

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