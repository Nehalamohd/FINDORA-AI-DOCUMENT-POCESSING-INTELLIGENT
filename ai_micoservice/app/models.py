from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean, UUID, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flows = relationship("Flow", back_populates="user", cascade="all, delete-orphan")

class Flow(Base):
    __tablename__ = "flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="flows")
    documents = relationship("Document", back_populates="flow", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="flow", cascade="all, delete-orphan")
    golden_qa = relationship("GoldenQA", back_populates="flow", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"))
    filename = Column(String)
    file_path = Column(String)
    file_type = Column(String)
    file_size = Column(Integer)
    total_pages = Column(Integer)
    status = Column(String, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    task_id = Column(String)
    error_message = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    flow = relationship("Flow", back_populates="documents")
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flow = relationship("Flow", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"))
    role = Column(String)  # 'user', 'assistant'
    content = Column(Text)
    retrieved_context = Column(Text) # Stored as JSON string or Text
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="messages")

class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    page_number = Column(Integer)
    content = Column(Text)

    document = relationship("Document", back_populates="pages")
    chunks = relationship("Chunk", back_populates="page", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"))
    chunk_index = Column(Integer)
    content = Column(Text)
    # tsv is handled by raw SQL/trigger in migrate.py, but we can define it if needed.
    # For now, we'll keep it as a placeholder or handle it via raw SQL in RAG.

    document = relationship("Document", back_populates="chunks")
    page = relationship("Page", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id", ondelete="CASCADE"))
    # 'vector' is a custom type from pgvector. We'll handle it carefully.
    # Since SQLAlchemy doesn't have it by default, we'll use a raw SQL for insertion if needed,
    # or just use the model for metadata.
    # embedding = Column(...)

    chunk = relationship("Chunk", back_populates="embeddings")

class GoldenQA(Base):
    __tablename__ = "golden_qa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("flows.id", ondelete="CASCADE"))
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flow = relationship("Flow", back_populates="golden_qa")
    evaluations = relationship("Evaluation", back_populates="golden", cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    golden_id = Column(UUID(as_uuid=True), ForeignKey("golden_qa.id", ondelete="CASCADE"))
    generated_answer = Column(Text)
    similarity_score = Column(Float)
    judge_feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    golden = relationship("GoldenQA", back_populates="evaluations")
