from sqlalchemy import create_engine
import os

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "findora_db",
    "user": "findora",
    "password": "findorapass"
}

DATABASE_URL = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

try:
    print(f"Testing connection to: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()
