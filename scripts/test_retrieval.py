import faiss
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os

load_dotenv()

# -----------------------------
# Load Gemini client
# -----------------------------
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# -----------------------------
# Load FAISS index
# -----------------------------
index = faiss.read_index("data/job_faiss.index")

# Load job chunks
df = pd.read_csv("data/job_chunks.csv")

# -----------------------------
# Student profile/query
# -----------------------------
query = """
Python developer with skills in Python, Flask, SQL, Java,
HTML, CSS, Git and web development. Looking for an entry-level
software development job.
"""

# -----------------------------
# Create query embedding
# -----------------------------
response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=query,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_QUERY",
        output_dimensionality=768
    )
)

query_vector = np.array(
    [response.embeddings[0].values],
    dtype="float32"
)

# Normalize query vector
faiss.normalize_L2(query_vector)

# -----------------------------
# Search FAISS
# -----------------------------
top_k = 5

scores, indices = index.search(query_vector, top_k)

# -----------------------------
# Display results
# -----------------------------
print("\n===== TOP MATCHING JOB CHUNKS =====\n")

for rank, (score, idx) in enumerate(
    zip(scores[0], indices[0]), start=1
):

    job = df.iloc[idx]

    print(f"Rank: {rank}")
    print(f"Similarity Score: {score:.4f}")
    print(f"Job Title: {job['jobtitle']}")
    print(f"Company: {job['company']}")
    print(f"Category: {job['category']}")
    print(f"Job ID: {job['jobid']}")
    print("-" * 60)