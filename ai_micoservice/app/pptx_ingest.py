from pptx import Presentation
from app.embedding import embed
from app.database import get_conn

def extract_text_from_pptx(pptx_path: str):
    """Extracts text slide by slide from a PPTX file."""
    prs = Presentation(pptx_path)
    for i, slide in enumerate(prs.slides):
        text_runs = []
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text_runs.append(shape.text)
        
        # Also try to get notes
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text
            if notes:
                text_runs.append(f"\nNotes: {notes}")
                
        yield i + 1, "\n".join(text_runs)

def ingest_pptx(file_path: str, filename: str, task_id: str = None, flow_id: str = None, username: str = None):
    """
    Ingests a PPTX file. Extracts text slide-by-slide.
    """
    with get_conn() as conn:
        with conn.cursor() as cur: 
            # Insert document with 'processing' status and task_id
            cur.execute(
                "INSERT INTO documents (filename, file_path, file_type, status, task_id, flow_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (filename, file_path, "pptx", "processing", task_id, flow_id)
            )
            document_id = cur.fetchone()["id"]

            try:
                print(f"Processing {filename} (PPTX)...")
                
                for slide_no, slide_text in extract_text_from_pptx(file_path):
                    if not slide_text.strip():
                        continue
                        
                    # Store page (slide)
                    cur.execute(
                        "INSERT INTO pages (document_id, page_number, content) VALUES (%s, %s, %s) RETURNING id",
                        (document_id, slide_no, slide_text)
                    )
                    page_id = cur.fetchone()["id"]

                    # Chunking Strategy: One Slide = One Chunk (unless very long)
                    # For simplicity, following the existing PDF pattern: one page/slide = one chunk
                    chunk_content = slide_text
                    embeddings = embed([chunk_content])
                    
                    if embeddings:
                        embedding = embeddings[0]
                        cur.execute(
                            "INSERT INTO chunks (document_id, page_id, chunk_index, content) VALUES (%s, %s, %s, %s) RETURNING id",
                            (document_id, page_id, 0, chunk_content)
                        )
                        chunk_id = cur.fetchone()["id"]
                        cur.execute(
                            "INSERT INTO embeddings (chunk_id, embedding) VALUES (%s, %s)",
                            (chunk_id, embedding)
                        )

                # Mark as completed
                cur.execute(
                    "UPDATE documents SET status = 'completed' WHERE id = %s",
                    (document_id,)
                )

            except Exception as e:
                cur.execute(
                    "UPDATE documents SET status = 'failed', error_message = %s WHERE id = %s",
                    (str(e), document_id)
                )
                conn.commit()
                raise e

            conn.commit()
    return document_id
