# Findora AI: Intelligent Document Processing Platform

**Findora AI** is a premium, high-performance RAG (Retrieval-Augmented Generation) application designed to solve information overload. It provides a bridge between raw document data—from dense PDFs to complex spreadsheets—and actionable knowledge.

---

## 🌟 Core Capabilities

### 💬 Smart RAG Chat
- **Deep Contextual Understanding**: Talk to your documents in plain English using advanced retrieval logic.
- **Streaming Responses**: Real-time message delivery powered by Groq LPU™ technology.
- **Interactive Citations**: Every answer includes clickable sources (File name & Page number) to ensure transparency.

### 📋 Proactive AI Reviewer
- **Quality Scoring**: Automatically assesses documents on a 1-10 scale.
- **Gap Identification**: Pinpoints missing information or inconsistencies.
- **Future Predictions**: Suggests improvements and innovation paths based on content.

### 🌐 Hybrid Search
- **Best of Both Worlds**: Combines Semantic Search (meaning-based) with Keyword Search (text-based).
- **Web Fallback**: If an answer isn't in your files, Findora securely searches the web (DuckDuckGo/Wikipedia) to provide a complete answer.

### 🚀 Parallel Ingestion
- **Speed**: Optimized with Celery workers for concurrent page processing.
- **OCR Fallback**: Automatically uses Vision Models (Llama 4 Scout) to extract text from images and charts.

---

## 🛠️ Technical Architecture

Findora AI is built on a modern, decoupled microservice architecture:

- **Frontend**: Streamlit-based "Premium" UI with dynamic animations and glassmorphic design.
- **Backend API**: FastAPI for high-concurrency, asynchronous requests.
- **Task Orchestration**: Celery workers with Redis for background document processing.
- **Database**: PostgreSQL with **PGVector** for storing and querying high-dimensional embeddings.
- **AI Engine**: Groq Inference (Llama 3.3 70B & Mixtral) for sub-second response times.

---

## 🏗️ Data Persistence & ORM

Findora AI uses a sophisticated data layer to manage complex relationships and high-dimensional vector data:

- **ORM Tool**: **SQLAlchemy 2.0** is utilized for Object-Relational Mapping, providing a Pythonic interface to the database while ensuring type safety and robust session management.
- **Database Engine**: **PostgreSQL** serves as the primary relational store, chosen for its stability and advanced feature set.
- **Vector Intelligence**: The **PGVector** extension is integrated directly into the database, allowing for high-performance similarity searches between document embeddings.
- **Data Models**:
    - `User`: Manages authentication and workspace isolation.
    - `Flow`: Logical containers for grouped documents and chat sessions.
    - `Document` & `Page`: Hierarchical storage of file metadata and content.
    - `Chunk` & `Embedding`: Atomic units of knowledge linked to vector representations for rapid retrieval.
    - `Message`: Persistent storage of chat interactions for long-term session memory.
- **Relationship Management**: Implements strict foreign key constraints and `ondelete="CASCADE"` rules to maintain referential integrity throughout the document lifecycle.

---

## 🛡️ Quality Assurance & Testing

Findora AI is "Hardened" for production standards through a multi-layered testing strategy using the **pytest** framework:

### 1. Unit Testing (Logic Layer)
- **Security (`test_auth.py`)**: Validates PBKDF2-SHA256 password hashing, JWT token creation, and complex dependency injection for user authentication.
- **Message Integrity (`test_chat.py`)**: Uses database mocking to verify that chat history is correctly retrieved, formatted, and persisted during failures.
- **AI Intelligence (`test_llm.py`)**: Tests Groq API connectivity, response streaming, and the exponential backoff retry logic for vision models.
- **Search Optimization (`test_rag.py`)**: Verifies the weightings (70% semantic, 30% keyword) of our hybrid search algorithm and the precision of dynamic prompt construction.

### 2. Integration Testing (API Layer)
- **API End-to-End (`test_api.py`)**: Utilizes FastAPI's `TestClient` to simulate real-world user flows:
    - User registration and duplicate detection.
    - Secure login and token issuance.
    - Document flow creation and retrieval.

### 3. Resilience Engineering
- **Exception Shielding**: Every core function in `chat.py`, `rag.py`, and `auth.py` is protected by custom error handlers that log technical data while returning user-friendly status codes (e.g., 503 for DB downtime).
- **Graceful UI Navigation**: Frontend navigation via `st.switch_page` is wrapped in safety nets to prevent application crashes if resources are temporarily unavailable.

---

## 📄 Setup & Usage

### Running Locally
1. Start the infrastructure: `docker-compose up -d`
2. Launch the backend: `cd ai_micoservice && uvicorn app.main:app`
3. Launch the UI: `cd frontend_streamlit && streamlit run app.py`

### Testing (Environment Specific)

#### Local Development
```bash
cd ai_micoservice
$env:PYTHONPATH="."  # PowerShell
PYTHONPATH=. pytest -v tests/  # Bash/WSL
```

#### Production (EC2 / Docker)
Run tests directly inside the running container to verify the production environment:
```bash
docker exec -it findora_api pytest -v tests/
```

---

## ☁️ AWS EC2 Deployment Guide

To push new code updates to your AWS EC2 instance, follow these steps using your specific credentials:

### 1. Connect to your Instance
Open your terminal and run the command matching your environment:

**For Windows (PowerShell):**
```powershell
ssh -i "C:\Users\NEHALA MOHAMED\Downloads\findora-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

**For WSL / Linux (Bash):**
WSL accesses your Windows files via `/mnt/c/`. You also need to fix file permissions:
```bash
# 1. Fix permissions (Linux requires the key to be private)
chmod 400 "/mnt/c/Users/NEHALA MOHAMED/Downloads/findora-key.pem"

# 2. Connect
ssh -i "/mnt/c/Users/NEHALA MOHAMED/Downloads/findora-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

### 2. Update the Codebase
Once logged into the EC2 instance, navigate to the project folder and pull the latest changes. 

**Note**: If you get an error saying `couldn't find remote ref main`, it means your code is on a different branch. Try pulling **`clean-sync-v1`**:

```bash
cd flow_intelligence
# Pull the specific active branch
git pull origin clean-sync-v1
```

### 2. Update the Codebase
... (previous content) ...

#### ⚠️ Troubleshooting: "Local changes would be overwritten"
If the `git pull` fails because of local changes on the EC2, run these commands to **discard those changes** and force-sync with the remote code:

```bash
# 1. Fetch latest updates
git fetch origin clean-sync-v1

# 2. Reset everything to match the GitHub branch exactly
# WARNING: This deletes any local modifications on the server
git reset --hard origin/clean-sync-v1

# 3. Clean untracked files that are causing blocks
git clean -fd
```

### 3. Deploy the Updates
Use Docker to rebuild the changed services and restart the application without downtime:
```bash
docker compose up -d --build
```

### 4. Verify the Logs
Ensure the backend is running correctly:
```bash
docker compose logs -f api
```

---
*Findora AI — Intelligence. Insights. Instant Clarity.*
