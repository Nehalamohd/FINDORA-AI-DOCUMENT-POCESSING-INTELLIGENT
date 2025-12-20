from PyPDF2 import PdfReader
from app.embedding import embed
from app.database import get_conn

def extract_text_by_page(pdf_path: str):
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        yield i + 1, page.extract_text()

def chunk_text(text, size=500):
    words = text.split()
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size])

def ingest_pdf(file_path: str, filename: str):
    with get_conn() as conn:
        cur = conn.cursor()

        # Insert document
        cur.execute(
            "INSERT INTO documents (filename, file_path, file_type) VALUES (%s, %s, %s) RETURNING id",
            (filename, file_path, "pdf")
        )
        document_id = cur.fetchone()["id"]

        # Process pages
        for page_no, page_text in extract_text_by_page(file_path):
            if not page_text:
                continue

            cur.execute(
                "INSERT INTO pages (document_id, page_number, content) VALUES (%s, %s, %s) RETURNING id",
                (document_id, page_no, page_text)
            )
            page_id = cur.fetchone()["id"]

            chunks = list(chunk_text(page_text))
            embeddings = embed(chunks)

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cur.execute(
                    "INSERT INTO chunks (document_id, page_id, chunk_index, content) VALUES (%s, %s, %s, %s) RETURNING id",
                    (document_id, page_id, idx, chunk)
                )
                chunk_id = cur.fetchone()["id"]

                cur.execute(
                    "INSERT INTO embeddings (chunk_id, embedding) VALUES (%s, %s)",
                    (chunk_id, embedding)
                )

        conn.commit()
