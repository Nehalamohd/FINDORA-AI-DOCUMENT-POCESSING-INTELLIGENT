from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL

model = SentenceTransformer(EMBEDDING_MODEL)
# for embedding texts
#input list of string output list of list of float
def embed(texts: list[str]) -> list[list[float]]:
    return model.encode(texts).tolist()
# 384-dimensional vector