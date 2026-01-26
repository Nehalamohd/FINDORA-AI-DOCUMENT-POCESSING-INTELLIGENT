# ORM & Database Schema Overview

This document provides a detailed technical overview of the PostgreSQL database schema managing the Findora AI application, implemented using explicit SQLAlchemy 2.0 ORM models.

## 1. Database Configuration
- **Database**: PostgreSQL
- **Extensions**: `vector` (pgvector) for embedding storage.
- **ORM**: SQLAlchemy 2.0 (Sync/Async compatible structure, currently using Sync `SessionLocal`).
- **Connection**: Managed via `app.database.get_db` dependency.

## 2. Core Models (`app/models.py`)

### User Management
| Model | Table Name | Description | Key Relationships |
|-------|------------|-------------|-------------------|
| `User` | `users` | Stores user credentials and profile info. | `flows` (One-to-Many), `daily_usage` (One-to-One) |

**Key Fields:**
- `id`: UUID (Primary Key)
- `email`: Unique String
- `hashed_password`: Bcrypt hash
- `is_active`: Boolean status

### Document Flow
| Model | Table Name | Description | Key Relationships |
|-------|------------|-------------|-------------------|
| `Flow` | `flows` | Represents a "Workspace" or collection of documents. | `user` (Many-to-One), `documents` (One-to-Many), `reviews` (One-to-One) |
| `Document` | `documents` | Metadata for uploaded files (PDF/PPTX). | `flow` (Many-to-One), `pages` (One-to-Many) |

### Content & Embeddings
| Model | Table Name | Description | Key Relationships |
|-------|------------|-------------|-------------------|
| `Page` | `pages` | Represents a single page of a document. | `document` (Many-to-One), `chunks` (One-to-Many) |
| `Chunk` | `chunks` | Small text segments used for RAG. | `page` (Many-to-One) |

**Embedding Vector:**
- The `Chunk` table contains a `embedding` column of type `Vector(384)`, compatible with the `all-MiniLM-L6-v2` model.

### Chat System
| Model | Table Name | Description | Key Relationships |
|-------|------------|-------------|-------------------|
| `Session` | `sessions` | Groups chat messages into a conversation context. | `flow` (Many-to-One), `messages` (One-to-Many) |
| `Message` | `messages` | Individual chat exchanges (User/Assistant). | `session` (Many-to-One) |

## 3. Usage Example

```python
from app.database import SessionLocal
from app.models import User, Flow

db = SessionLocal()

# Query high-level relationships
user = db.query(User).filter_by(username="jdoe").first()
for flow in user.flows:
    print(f"Flow: {flow.name} has {len(flow.documents)} documents")
```

## 4. Migration Strategy
Database migrations are handled by checking for table existence on startup in `app/migrate.py`. For production schema changes, we recommend integrating `alembic`.
