"""
Text embedding utility using SentenceTransformers.
"""
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL
from app.logger import logger

model = SentenceTransformer(EMBEDDING_MODEL)
# for embedding texts
#input list of string output list of list of float
def embed(texts: list[str]) -> list[list[float]]:
    """
    Converts a list of strings into a list of vector embeddings (384 dimensions).
    """
    logger.debug(f"Embedding {len(texts)} text segments")
    try:
        return model.encode(texts).tolist()
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        # Return empty list or zeros depending on expected behavior. 
        # Most callers expect a list of lists.
        return []
# 384-dimensional vector