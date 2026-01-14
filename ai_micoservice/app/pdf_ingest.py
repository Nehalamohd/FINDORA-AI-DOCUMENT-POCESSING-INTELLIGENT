from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import base64
from app.embedding import embed
from app.database import SessionLocal
from app.models import Document, Page, Chunk, Embedding
from app.llm import analyze_image
from sqlalchemy import text
from app.logger import logger

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
def process_pdf_page(document_id: int, page_no: int, file_path: str):
    """Processes a single PDF page: tries direct extraction, falls back to vision."""
    db = SessionLocal()
    try:
        # 1. Try Direct Extraction with fitz
        doc = fitz.open(file_path)
        page_obj = doc[page_no - 1]
        extracted_text = page_obj.get_text().strip()
        doc.close()

        # 2. Fallback to Vision if text is too sparse (e.g., a scan or image-only plan)
        if len(extracted_text) < 50:
            logger.info(f"Page {page_no}: Sparse text ({len(extracted_text)} chars). Falling back to Vision...")
            # Re-open for image conversion
            doc = fitz.open(file_path)
            page_obj = doc[page_no - 1]
            zoom = 200 / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page_obj.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("jpeg")
            base64_img = base64.b64encode(img_data).decode("utf-8")
            doc.close()
            
            vision_text = analyze_image(base64_img)
            if vision_text:
                extracted_text = vision_text

        if not extracted_text:
            return None

        # 3. Store Page
        page = Page(document_id=document_id, page_number=page_no, content=extracted_text)
        db.add(page)
        db.commit()
        db.refresh(page)
        page_id = page.id

        # 4. Chunk & Embed
        embeddings = embed([extracted_text])
        if embeddings:
            embedding = embeddings[0]
            chunk = Chunk(document_id=document_id, page_id=page_id, chunk_index=0, content=extracted_text)
            db.add(chunk)
            db.commit()
            db.refresh(chunk)
            chunk_id = chunk.id
            
            db.execute(
                text("INSERT INTO embeddings (chunk_id, embedding) VALUES (:chunk_id, CAST(:embedding AS vector))"),
                {"chunk_id": chunk_id, "embedding": str(embedding.tolist()) if hasattr(embedding, 'tolist') else str(embedding)}
            )
            db.commit()
        return page_id
    finally:
        db.close()

def ingest_pdf(file_path: str, filename: str, task_id: str = None, flow_id: str = None, username: str = None):
    db = SessionLocal()
    try:
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

        # Get total pages
        pdf_doc = fitz.open(file_path)
        total_pages = len(pdf_doc)
        pdf_doc.close()

        logger.info(f"Processing {filename}: {total_pages} pages...")
        
        # Parallel processing will be handled by tasks.py
        # For now, we still have the sequential fallback here if called directly
        for page_no in range(1, total_pages + 1):
            process_pdf_page(document_id, page_no, file_path)

        doc.status = 'completed'
        db.commit()
        return document_id
    except Exception as e:
        db.rollback()
        db.execute(
            text("UPDATE documents SET status = 'failed', error_message = :err WHERE task_id = :tid"),
            {"err": str(e), "tid": task_id}
        )
        db.commit()
        raise e
    finally:
        db.close()

    return document_id # return id for tracking status