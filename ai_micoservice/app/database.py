from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, DB_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor

# SQLAlchemy Setup
engine = create_engine(DATABASE_URL)
#just create session not connect yet
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#yield is hands the db session to route ,cleanup
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Legacy connection for backward compatibility during migration
def get_conn():
    return psycopg2.connect(
        cursor_factory=RealDictCursor,
        **DB_CONFIG
    )
