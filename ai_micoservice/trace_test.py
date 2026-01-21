"""
Simple script to trace database connection issues and print detailed stack traces.
"""
import traceback
import sys
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

try:
    print(f"Testing DATABASE_URL: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print(f"Result: {res.fetchone()}")
    print("SUCCESS")
except Exception:
    traceback.print_exc()
    sys.exit(1)
