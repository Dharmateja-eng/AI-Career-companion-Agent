import pandas as pd
import re

# Input and output files
input_file = "data/job_postings_clean.csv"
output_file = "data/job_chunks.csv"

# Load cleaned jobs
df = pd.read_csv(input_file)

print("Jobs loaded:", len(df))


# --------------------------------------------------
# Clean text before chunking
# --------------------------------------------------

def clean_text(text):
    text = str(text)

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remove email addresses
    text = re.sub(r"\S+@\S+", " ", text)

    # Remove phone numbers
    text = re.sub(r"\b\d{10}\b", " ", text)

    # Remove common promotional phrases
    promotional_phrases = [
        "send me jobs like this",
        "download ppt",
        "view contact details",
        "apply now",
        "what are you waiting for",
        "grab best opportunity",
        "contact us",
        "contact details"
    ]

    for phrase in promotional_phrases:
        text = re.sub(
            re.escape(phrase),
            " ",
            text,
            flags=re.IGNORECASE
        )

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# --------------------------------------------------
# Create chunks
# --------------------------------------------------

chunks = []

for _, row in df.iterrows():

    job_text = (
        f"Job Title: {row['jobtitle']}\n"
        f"Company: {row['company']}\n"
        f"Category: {row['category']}\n"
        f"Skills: {row['skills']}\n"
        f"Experience: {row['experience']}\n"
        f"Education: {row['education']}\n"
        f"Industry: {row['industry']}\n"
        f"Location: {row['joblocation_address']}\n"
        f"Job Description: {row['jobdescription']}"
    )

    # Clean the complete job text
    job_text = clean_text(job_text)

    # Split into words
    words = job_text.split()

    # Number of words per chunk
    chunk_size = 150

    # Create chunks
    for start in range(0, len(words), chunk_size):

        chunk_words = words[start:start + chunk_size]

        chunk_text = " ".join(chunk_words)

        chunks.append({
            "jobid": row["jobid"],
            "jobtitle": row["jobtitle"],
            "company": row["company"],
            "category": row["category"],
            "experience": row["experience"],
            "chunk_id": len(chunks),
            "chunk_text": chunk_text
        })


# --------------------------------------------------
# Save chunks
# --------------------------------------------------

chunks_df = pd.DataFrame(chunks)

chunks_df.to_csv(
    output_file,
    index=False
)


# --------------------------------------------------
# Display results
# --------------------------------------------------

print("--------------------------------")
print("Job chunking completed!")
print("--------------------------------")

print("Jobs:", len(df))
print("Chunks:", len(chunks_df))

print("Saved to:", output_file)

print("\nColumns:")
print(list(chunks_df.columns))

print("\nFirst chunk:")
print(chunks_df["chunk_text"].iloc[0])