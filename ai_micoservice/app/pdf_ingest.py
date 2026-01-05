from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import base64
from app.embedding import embed
from app.database import SessionLocal
from app.models import Document, Page, Chunk, Embedding
from app.llm import analyze_image
from sqlalchemy import text

# for extracting text by page
#yield for one page at a time
#to extract text from each page along with its page number
def extract_text_by_page(pdf_path: str):
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        yield i + 1, page.extract_text()

# for converting PDF pages to base64 images
#render PDF pages as images
#200 dpi
def convert_pdf_to_base64_images(pdf_path: str):
    """Converts each page of a PDF to a base64 encoded JPEG image at 200 DPI."""
    doc = fitz.open(pdf_path) #open the pdf file
    # 200 DPI calculation: 200 / 72 = 2.777...
    zoom = 200 / 72
    matrix = fitz.Matrix(zoom, zoom)#transformation matrix for scaling
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix) #page to image
        img_data = pix.tobytes("jpeg")#img to jpeg
        base64_img = base64.b64encode(img_data).decode("utf-8")
        yield i + 1, base64_img  #return page number and base64 image


# for chunking text
def chunk_text(text, size=500):
    words = text.split()
    #LLMs cannot handle very long text all at once
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size]) #string

#To take a PDF file, extract its content page by page using a Vision model (like Groq Vision)
# create embeddings for each page (or chunk), 
# and store everything in a relational database
# for ingesting PDF
def ingest_pdf(file_path: str, filename: str, task_id: str = None, flow_id: str = None, username: str = None):
    """
    Ingests a PDF. Uses Groq Vision to extract text/structure.
    One page is treated as one chunk.
    """
    db = SessionLocal()
    try:
        # Insert document with 'processing' status and task_id
        doc = Document(
            filename=filename,
            file_path=file_path,
            file_type="pdf",
            status="processing",
            task_id=task_id,
            flow_id=flow_id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        document_id = doc.id

        print(f"Processing {filename} with Vision Model (200 DPI)...")
        
        for page_no, base64_img in convert_pdf_to_base64_images(file_path):
            # Use Groq to extract text from image
            extracted_text = analyze_image(base64_img)
            #if no text in image,skip that page
            if not extracted_text:
                continue
                
            # Store page to db link to doc_id
            page = Page(document_id=document_id, page_number=page_no, content=extracted_text)
            db.add(page)
            db.commit()
            db.refresh(page)
            page_id = page.id

            # Chunking Strategy: One Page = One Chunk
            chunk_content = extracted_text
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
        db.rollback()  # Crucial to reset transaction state
        if 'doc' in locals():
            try:
                # Need to refetch or use a fresh status update after rollback
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

    return document_id # return id for tracking status
