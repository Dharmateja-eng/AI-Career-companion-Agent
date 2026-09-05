import pandas as pd
import re

# Input and output files
input_file = "data/job_postings.csv"
output_file = "data/job_postings_clean.csv"

# Load the 200 curated jobs
df = pd.read_csv(input_file)

print("Original rows:", len(df))


# --------------------------------------------------
# 1. Fill missing values
# --------------------------------------------------

fill_columns = [
    "skills",
    "education",
    "joblocation_address",
    "payrate",
    "postdate"
]

for column in fill_columns:
    df[column] = df[column].fillna("Not specified")


# --------------------------------------------------
# 2. Clean text fields
# --------------------------------------------------

text_columns = [
    "jobtitle",
    "company",
    "jobdescription",
    "skills",
    "experience",
    "education",
    "industry",
    "joblocation_address",
    "payrate"
]

for column in text_columns:
    df[column] = (
        df[column]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


# --------------------------------------------------
# 3. Clean job descriptions
# --------------------------------------------------

def clean_description(text):
    text = str(text)

    # Remove email addresses
    text = re.sub(r"\S+@\S+", " ", text)

    # Remove 10-digit phone numbers
    text = re.sub(r"\b\d{10}\b", " ", text)

    # Remove excessive spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


df["jobdescription"] = df["jobdescription"].apply(clean_description)


# --------------------------------------------------
# 4. Remove duplicate jobs
# --------------------------------------------------

before_duplicates = len(df)

df = df.drop_duplicates(
    subset=["jobtitle", "company", "jobdescription"]
)

duplicates_removed = before_duplicates - len(df)

print("Duplicates removed:", duplicates_removed)


# --------------------------------------------------
# 5. Remove very short descriptions
# --------------------------------------------------

df = df[
    df["jobdescription"].str.len() >= 100
].copy()

print("Rows after description filtering:", len(df))


# --------------------------------------------------
# 6. Create combined text for RAG
# --------------------------------------------------

df["search_text"] = (
    "Job Title: " + df["jobtitle"] +
    "\nCompany: " + df["company"] +
    "\nCategory: " + df["category"] +
    "\nSkills: " + df["skills"] +
    "\nExperience: " + df["experience"] +
    "\nEducation: " + df["education"] +
    "\nIndustry: " + df["industry"] +
    "\nLocation: " + df["joblocation_address"] +
    "\nJob Description: " + df["jobdescription"]
)


# --------------------------------------------------
# 7. Save cleaned dataset
# --------------------------------------------------

df.to_csv(
    output_file,
    index=False
)


# --------------------------------------------------
# 8. Display results
# --------------------------------------------------

print("\n--------------------------------")
print("Clean dataset created!")
print("--------------------------------")

print("Rows:", len(df))

print("Columns:")
print(list(df.columns))

print("\nSaved to:")
print(output_file)

print("\nMissing values:")
print(df.isnull().sum())

print("\nFirst job:")
print(df["search_text"].iloc[0][:1000])