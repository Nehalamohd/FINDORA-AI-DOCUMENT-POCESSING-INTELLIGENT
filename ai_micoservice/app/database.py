from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL, DB_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor
from app.logger import logger

# SQLAlchemy Setup
engine = create_engine(DATABASE_URL)
#just create session not connect yet
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#yield is hands the db session to route ,cleanup
def get_db():
    """
    Generator for database sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_conn():
    """
    Creates and returns a legacy psycopg2 database connection.
    """
    logger.debug("Creating legacy psycopg2 connection")
    try:
        return psycopg2.connect(
            cursor_factory=RealDictCursor,
            **DB_CONFIG
        )
    except Exception as e:
        logger.error(f"Failed to connect to database using psycopg2: {str(e)}")
        raise e
