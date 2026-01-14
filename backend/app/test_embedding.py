#Test embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

text = "This is a test sentence for embeddings"
embedding = model.encode(text)

print("Embedding length:", len(embedding))
print(embedding[:10])  # first 10 values
