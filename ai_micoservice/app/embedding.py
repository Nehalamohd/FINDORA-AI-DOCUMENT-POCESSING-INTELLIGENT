from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL

model = SentenceTransformer(EMBEDDING_MODEL)

def embed(texts: list[str]) -> list[list[float]]:
    return model.encode(texts).tolist()
