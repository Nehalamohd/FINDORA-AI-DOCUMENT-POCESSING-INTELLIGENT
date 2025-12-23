# Findora AI: RAG Chatbot Implementation Plan

As a senior AI engineer, I have reviewed your requirements and existing codebase. Below is the comprehensive implementation plan for **Findora AI**, focusing on the advanced PDF-to-Vision pipeline, asynchronous task management, and microservice architecture.

## 1. Architectural Overview

We will utilize a **Hub-and-Spoke** microservice architecture:
- **API Gateway (Backend/AI Service)**: Fast API entry point for file uploads, status checks, and chat orchestration.
- **Task Worker (Celery)**: Discrete processing unit for heavy-duty OCR (Groq Vision), text chunking, and vector embedding.
- **Message Broker (Redis)**: Orchestrates tasks and stores transient state.
- **Vector Database (PostgreSQL + pgvector)**: Long-term storage for documents, metadata, and embeddings.

---

## 2. Implementation Phases

### Phase 1: Database Schema Finalization
We will enhance the existing schema to explicitly track `celery_task_id` for real-time status retrieval.

- **`documents` table**: Add `task_id` (UUID) and `metadata` (JSONB).
- **`embeddings` table**: Ensure the vector dimension matches our embedding model (e.g., 384 or 768).

### Phase 2: High-Resolution Vision Pipeline
The "OCR replacement" logic using Groq Vision requires precise image formatting.
- **Image Conversion**: Utilize `PyMuPDF (fitz)` to render PDF pages at **200 DPI**.
- **Extraction Logic**: Each image is sent to the `llama-3.2-90b-vision-preview` model via Groq API.
- **Chunking Strategy**: 
    - **1 Page = 1 Chunk**: To maintain layout context, we treat each page's extracted text as a single atomic chunk.
    - **Metadata Linking**: Each chunk will be linked to its original page number and image path.

### Phase 3: Async Task Management (Celery + Redis)
- **Upload Flow**: 
    1. Frontend posts PDF -> Backend saves file to `/tmp`.
    2. Backend creates record in DB with `status=processing`.
    3. Backend triggers Celery task and returns `task_id` immediately.
- **Status Flow**:
    1. Frontend polls `GET /status/{task_id}`.
    2. Backend queries Redis Celery backend or DB record for current status.

---

## 3. API Design

### Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/upload` | Upload PDF. Returns `task_id` and `document_id`. |
| `GET` | `/api/v1/status/{task_id}` | Check processing progress (pending, processing, completed, failed). |
| `POST` | `/api/v1/chat` | Query the RAG system with a question + `flow_id`. |
| `GET` | `/api/v1/flows` | List available document collections. |

---

## 4. UI/UX Design (Findora Dashboard)
The UI will be designed for professional speed and clarity. (See visual mockup provided).

- **Glassmorphic Fluid Interface**: Dark mode with purple/blue accents.
- **Real-time Progress Pins**: Visual indicators for background processing.
- **Context-Aware Chat**: Messages show "Source Citations" which are the specific pages used for the answer.

---

## 5. Next Steps (Action Items)
1. **Consolidate Services**: I will align the `ai_micoservice` and `backend` directories to avoid logic duplication.
2. **Update `pdf_ingest.py`**: Refactor to support 200 DPI and one-page-per-chunk strategy.
3. **Implement `/verify` endpoint**: Create the logic to query task status across Redis and DB.
