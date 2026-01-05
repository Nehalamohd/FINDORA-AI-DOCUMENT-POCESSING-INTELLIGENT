import os

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": 5432,
    "dbname": "findora_db",
    "user": "findora",
    "password": "findorapass"
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"

# Other configurations
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30