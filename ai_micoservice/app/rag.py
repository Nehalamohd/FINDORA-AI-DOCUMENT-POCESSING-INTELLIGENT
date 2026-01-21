"""
RAG (Retrieval-Augmented Generation) core logic including hybrid search.
"""
from app.embedding import embed
from app.database import SessionLocal
from sqlalchemy import text
from app.logger import logger

def retrieve_chunks(query: str, top_k=5, flow_id: str = None):
    """
    Retrieves most relevant document chunks using hybrid search (semantic + keyword).
    
    Args:
        query (str): The search query.
        top_k (int): Number of chunks to return.
        flow_id (str): UUID of the flow to search within.
        
    Returns:
        list[dict]: List of chunks with content and metadata.
    """
    #create embedding for the query
    logger.debug(f"Retrieving chunks for query: '{query[:50]}...' (flow_id: {flow_id})")
    try:
        embeddings = embed([query])
        if not embeddings:
            logger.warning(f"Failed to generate embedding for query: {query[:50]}")
            return []
        q_emb = embeddings[0]
    except Exception as e:
        logger.error(f"Error during query embedding: {str(e)}")
        return []
    
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

    SELECT c.content, d.filename, p.page_number,
           COALESCE(s.score, 0) * 0.7 + COALESCE(k.score, 0) * 0.3 AS hybrid_score
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    LEFT JOIN pages p ON c.page_id = p.id
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
        logger.info(f"Hybrid search returned {len(rows)} chunks for query: '{query[:50]}...'")
        # Returns list of dicts with content, metadata, and score
        return [
            {"content": r[0], "filename": r[1], "page_number": r[2], "score": float(r[3])} 
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Hybrid search failed for query '{query[:50]}': {str(e)}")
        return []
    finally:
        db.close()
#for fetching first n chunks of a flow wen user asks for overview
def get_first_chunks(flow_id: str, limit: int = 10):
    """
    Force-retrieves the first N chunks of a flow, regardless of similarity.
    Used for meta-queries (summarize, overview) when search results are empty.
    """
    sql = """
    SELECT c.content, d.filename, 0 as page_number, 0.5 as hybrid_score
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.flow_id = CAST(:flow_id AS uuid)
    ORDER BY d.created_at ASC, c.id ASC
    LIMIT :limit;
    """
    db = SessionLocal()
    try:
        result = db.execute(text(sql), {"flow_id": flow_id, "limit": limit})
        rows = result.fetchall()
        logger.info(f"Force-retrieved {len(rows)} chunks for flow: {flow_id}")
        return [
            {"content": r[0], "filename": r[1], "page_number": r[2], "score": float(r[3])} 
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Failed to force-retrieve chunks for flow {flow_id}: {str(e)}")
        return []
    finally:
        db.close()

def build_prompt(context_chunks: list[dict], chat_history: list[dict], question: str, web_results: list[str] = None):
    """
    Constructs a detailed prompt for the LLM using retrieved context and history.
    """
    # Prepare Document Context with metadata
    #text from chunks with filename and page no
    doc_context_parts = []
    for chunk in context_chunks:
        filename = chunk.get("filename", "Unknown")
        page = chunk.get("page_number", "?")
        doc_context_parts.append(f"[File: {filename}, Page: {page}]\n{chunk['content']}")
    
    doc_context = "\n\n".join(doc_context_parts) if doc_context_parts else ""
    
    # Prepare Web Context search results

    web_context = ""
    if web_results:
        web_context = "\n\n".join(web_results)
    #chat history formatting
    history = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    
    # Determine if web search was truly active
    web_search_active = "YES" if web_results and len(web_results) > 0 else "NO"
    
    prompt = f"""
You are Findora AI, a helpful and expert assistant.
Your goal is to provide accurate, COMPREHENSIVE, and DETAILED answers using the provided Context sources.

[TONE AND DETAIL RULES]
- If a user asks to 'explain', 'describe', or 'summarize', provide a long, thorough, and step-by-step response.
- Do NOT be overly brief. Use multiple paragraphs and bullet points where appropriate to add depth.
- If you have enough information in the context, aim for a multi-paragraph explanation.

[STRICT CITATION RULES]
1. If "Document Context" provides a direct answer, use it and cite the filename/page.
2. If "Document Context" is missing or irrelevant (noise), you MUST use the "Web Search Context" if it is available.
3. [CRITICAL] Do not say "I do not have information" if there is "Web Search Context" provided that can answer the question.
4. ONLY mention "(Source: Web)" at the end of your answer if web results were the primary source.
5. If the answer is found in the documents, prioritized it and do NOT mention the web.
6. If both contexts are missing or truly irrelevant to the question, you may use your internal knowledge to provide a helpful answer, but clearly state that the information is NOT from the provided documents.

Chat History:
{history}

Document Context:
{doc_context if doc_context else "None (IMPORTANT: No documents matched this query)."}

Web Search Context (Active: {web_search_active}):
{web_context if web_results else "None available/DISABLED. DO NOT cite web sources."}

Question:
{question}

Answer:
"""
    # print(f"[DEBUG] Full Prompt: {prompt}")
    return prompt