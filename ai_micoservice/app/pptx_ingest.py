from pptx import Presentation
from app.embedding import embed
from app.database import SessionLocal
from app.models import Document, Page, Chunk, Embedding
from sqlalchemy import text

def extract_text_from_pptx(pptx_path: str):
    """Extracts text slide by slide from a PPTX file."""
    prs = Presentation(pptx_path)
    for i, slide in enumerate(prs.slides):
        text_runs = []
        #loop over all shapes in slide like table ,box
        for shape in slide.shapes:
            if hasattr(shape, "text"): #ensure shape has text property
                text_runs.append(shape.text)
        
        # Also try to get notes from slide
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text
            if notes:
                text_runs.append(f"\nNotes: {notes}")
                
        yield i + 1, "\n".join(text_runs)

def ingest_pptx(file_path: str, filename: str, task_id: str = None, flow_id: str = None, username: str = None):
    """
    Ingests a PPTX file. Extracts text slide-by-slide.
    """
    db = SessionLocal()
    try:
        # Insert document with 'processing' status and task_id
        doc = Document(
            filename=filename,
            file_path=file_path,
            file_type="pptx",
            status="processing",
            task_id=task_id,
            flow_id=flow_id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        document_id = doc.id

        print(f"Processing {filename} (PPTX)...")
        
        for slide_no, slide_text in extract_text_from_pptx(file_path):
            if not slide_text.strip():
                continue
                
            # Store page (slide)
            page = Page(document_id=document_id, page_number=slide_no, content=slide_text)
            db.add(page)
            db.commit()
            db.refresh(page)
            page_id = page.id

            # Chunking Strategy: One Slide = One Chunk (unless very long)
            # For simplicity, following the existing PDF pattern: one page/slide = one chunk
            chunk_content = slide_text
            embeddings = embed([chunk_content])
            
            if embeddings:
                embedding = embeddings[0]
                chunk = Chunk(document_id=document_id, page_id=page_id, chunk_index=0, content=chunk_content)
                db.add(chunk)
                db.commit()
                db.refresh(chunk)
                chunk_id = chunk.id
                
                # Insert embedding record (we'll update the vector column using raw SQL 
                # because standard SQLAlchemy doesn't support the 'vector' type without extensions)
                db.execute(
                    text("INSERT INTO embeddings (chunk_id, embedding) VALUES (:chunk_id, CAST(:embedding AS vector))"),
                    {"chunk_id": chunk_id, "embedding": str(embedding.tolist()) if hasattr(embedding, 'tolist') else str(embedding)}
                )
                db.commit()

        # Mark as completed
        doc.status = 'completed'
        db.commit()

    except Exception as e:
        db.rollback()
        if 'doc' in locals():
            try:
                db.execute(
                    text("UPDATE documents SET status = 'failed', error_message = :err WHERE task_id = :tid"),
                    {"err": str(e), "tid": task_id}
                )
                db.commit()
            except Exception as inner_e:
                print(f"Failed to log error to DB: {inner_e}")
        raise e
    finally:
        db.close()
        
    return document_id
