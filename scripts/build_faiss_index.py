import faiss
import numpy as np

EMBEDDINGS_FILE = "data/job_embeddings.npy"
INDEX_FILE = "data/job_faiss.index"

# Load embeddings
embeddings = np.load(EMBEDDINGS_FILE).astype("float32")

print("Embeddings loaded:", embeddings.shape)

# Create FAISS index
dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(dimension)

# Normalize embeddings for cosine similarity
faiss.normalize_L2(embeddings)

# Add embeddings to index
index.add(embeddings)

# Save index
faiss.write_index(index, INDEX_FILE)

print("FAISS index created successfully!")
print("Number of vectors:", index.ntotal)
print("Vector dimensions:", dimension)
print("Saved to:", INDEX_FILE)