from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import base64
from app.embedding import embed
from app.database import get_conn
from app.llm import analyze_image

def extract_text_by_page(pdf_path: str):
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        yield i + 1, page.extract_text()

def convert_pdf_to_base64_images(pdf_path: str):
    """Converts each page of a PDF to a base64 encoded JPEG image at 200 DPI."""
    doc = fitz.open(pdf_path)
    # 200 DPI calculation: 200 / 72 = 2.777...
    zoom = 200 / 72
    matrix = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix) 
        img_data = pix.tobytes("jpeg")
        base64_img = base64.b64encode(img_data).decode("utf-8")
        yield i + 1, base64_img

def chunk_text(text, size=500):
    words = text.split()
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size])

def ingest_pdf(file_path: str, filename: str, task_id: str = None, flow_id: str = None):
    """
    Ingests a PDF. Uses Groq Vision to extract text/structure.
    One page is treated as one chunk.
    """
    with get_conn() as conn:
        with conn.cursor() as cur: 
            # Insert document with 'processing' status and task_id
            cur.execute(
                "INSERT INTO documents (filename, file_path, file_type, status, task_id, flow_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (filename, file_path, "pdf", "processing", task_id, flow_id)
            )
            document_id = cur.fetchone()["id"]

            try:
                print(f"Processing {filename} with Vision Model (200 DPI)...")
                
                for page_no, base64_img in convert_pdf_to_base64_images(file_path):
                    # Use Groq to extract text from image
                    extracted_text = analyze_image(base64_img)
                    
                    if not extracted_text:
                        continue
                        
                    # Store page
                    cur.execute(
                        "INSERT INTO pages (document_id, page_number, content) VALUES (%s, %s, %s) RETURNING id",
                        (document_id, page_no, extracted_text)
                    )
                    page_id = cur.fetchone()["id"]

                    # Chunking Strategy: One Page = One Chunk
                    chunk_content = extracted_text
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
