import os
import time
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

INPUT_FILE = "data/job_chunks.csv"
OUTPUT_FILE = "data/job_embeddings.npy"

df = pd.read_csv(INPUT_FILE)

total_chunks = len(df)

print(f"Chunks to embed: {total_chunks}")

# Load existing embeddings if available
if os.path.exists(OUTPUT_FILE):
    embeddings = np.load(OUTPUT_FILE).tolist()
    start_index = len(embeddings)

    print(f"Existing embeddings found: {start_index}")
    print(f"Resuming from chunk {start_index + 1}")
else:
    embeddings = []
    start_index = 0

for i in range(start_index, total_chunks):

    text = str(df.iloc[i]["chunk_text"])

    print(f"Embedding {i + 1}/{total_chunks}")

    for attempt in range(3):

        try:
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )

            vector = response.embeddings[0].values
            embeddings.append(vector)

            # Save progress after every embedding
            np.save(
                OUTPUT_FILE,
                np.array(embeddings, dtype=np.float32)
            )

            break

        except Exception as e:

            print(
                f"Error on chunk {i + 1}, "
                f"attempt {attempt + 1}/3"
            )

            print(e)

            if attempt < 2:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Failed after 3 attempts.")
                print("Stopping so progress is not lost.")
                raise

    time.sleep(0.2)

print("\nEmbedding completed successfully!")
print("Number of embeddings:", len(embeddings))
print("Embedding dimensions:", len(embeddings[0]))
print("Saved to:", OUTPUT_FILE)