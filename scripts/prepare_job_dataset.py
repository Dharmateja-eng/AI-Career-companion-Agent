import pandas as pd
import re

# --------------------------------------------------
# 1. Load the raw dataset
# --------------------------------------------------

input_file = "data/jobs_raw.csv"
output_file = "data/job_postings.csv"

df = pd.read_csv(input_file)

print("Original rows:", len(df))


# --------------------------------------------------
# 2. Keep only useful columns for our RAG system
# --------------------------------------------------

useful_columns = [
    "jobtitle",
    "company",
    "jobdescription",
    "skills",
    "experience",
    "education",
    "industry",
    "joblocation_address",
    "payrate",
    "postdate",
    "jobid"
]

df = df[useful_columns].copy()


# --------------------------------------------------
# 3. Replace missing values
# --------------------------------------------------

df = df.fillna("")


# --------------------------------------------------
# 4. Combine important text for filtering
# --------------------------------------------------

text_columns = [
    "jobtitle",
    "jobdescription",
    "skills",
    "industry"
]

df["combined_text"] = (
    df[text_columns]
    .astype(str)
    .agg(" ".join, axis=1)
    .str.lower()
)


# --------------------------------------------------
# 5. Select technical / career-related jobs
# --------------------------------------------------

technical_keywords = [
    "software",
    "developer",
    "development",
    "engineer",
    "python",
    "java",
    "javascript",
    "frontend",
    "front end",
    "backend",
    "back end",
    "full stack",
    "web developer",
    "web development",
    "android",
    "ios",
    "mobile",
    "data analyst",
    "data scientist",
    "data science",
    "machine learning",
    "artificial intelligence",
    "artificial intelligence",
    "ai ",
    "deep learning",
    "sql",
    "database",
    "cloud",
    "devops",
    "aws",
    "azure",
    "power bi",
    "tableau",
    "analytics",
    "business analyst",
    "ui developer",
    "ui/ux",
    "testing",
    "qa engineer",
    "automation",
    "cyber security",
    "cybersecurity",
    "network engineer",
    "technical support"
]

pattern = "|".join(re.escape(keyword) for keyword in technical_keywords)

df = df[df["combined_text"].str.contains(pattern, regex=True, na=False)]

print("After technical filtering:", len(df))


# --------------------------------------------------
# 6. Remove obvious irrelevant / low-quality jobs
# --------------------------------------------------

unwanted_keywords = [
    "data entry",
    "work from home",
    "part time",
    "part-time",
    "medical coding",
    "telecaller",
    "telecaller",
    "sales executive",
    "sales manager",
    "business development executive",
    "business development manager",
    "marketing executive",
    "marketing manager",
    "insurance",
    "form filling",
    "captcha",
    "whatsapp",
    "earn money",
    "typing job"
]

unwanted_pattern = "|".join(
    re.escape(keyword) for keyword in unwanted_keywords
)

df = df[
    ~df["combined_text"].str.contains(
        unwanted_pattern,
        regex=True,
        na=False
    )
]

print("After removing irrelevant jobs:", len(df))


# --------------------------------------------------
# 7. Prefer fresher / entry-level jobs
# --------------------------------------------------

experience_text = df["experience"].astype(str).str.lower()

entry_level_keywords = [
    "0 - 1",
    "0 - 2",
    "0 - 3",
    "0-1",
    "0-2",
    "0-3",
    "fresher",
    "freshers",
    "entry level",
    "junior"
]

entry_pattern = "|".join(
    re.escape(keyword) for keyword in entry_level_keywords
)

entry_level = df[
    experience_text.str.contains(
        entry_pattern,
        regex=True,
        na=False
    )
]

print("Entry-level jobs available:", len(entry_level))


# --------------------------------------------------
# 8. Remove duplicate job descriptions
# --------------------------------------------------

df = df.drop_duplicates(
    subset=["jobtitle", "company", "jobdescription"]
)

print("After removing duplicates:", len(df))


# --------------------------------------------------
# 9. Remove jobs with very small descriptions
# --------------------------------------------------

df = df[
    df["jobdescription"].astype(str).str.len() >= 100
]

print("After description quality filtering:", len(df))


# --------------------------------------------------
# 10. Select jobs from different categories
# --------------------------------------------------

categories = {
    "Software Development": [
        "software developer",
        "software engineer",
        "application developer",
        "java developer",
        "python developer",
        "php developer",
        ".net developer"
    ],

    "Web Development": [
        "web developer",
        "web designer",
        "frontend",
        "front end",
        "backend",
        "back end",
        "full stack"
    ],

    "Data / AI": [
        "data analyst",
        "data scientist",
        "data science",
        "machine learning",
        "artificial intelligence",
        "ai developer"
    ],

    "Mobile Development": [
        "android developer",
        "ios developer",
        "mobile developer"
    ],

    "Database / SQL": [
        "sql developer",
        "database",
        "pl/sql",
        "mysql",
        "oracle"
    ],

    "Cloud / DevOps": [
        "cloud",
        "devops",
        "aws",
        "azure"
    ],

    "Testing": [
        "qa engineer",
        "software testing",
        "test engineer",
        "automation testing"
    ],

    "Analytics": [
        "business analyst",
        "business intelligence",
        "power bi",
        "tableau",
        "analytics"
    ]
}


# --------------------------------------------------
# 11. Allocate jobs across categories
# --------------------------------------------------

selected_parts = []

jobs_per_category = 25

for category, keywords in categories.items():

    category_pattern = "|".join(
        re.escape(keyword) for keyword in keywords
    )

    category_df = df[
        df["jobtitle"]
        .astype(str)
        .str.lower()
        .str.contains(category_pattern, regex=True, na=False)
    ]

    # Prefer entry-level jobs first
    category_entry = category_df[
        category_df["experience"]
        .astype(str)
        .str.lower()
        .str.contains(entry_pattern, regex=True, na=False)
    ]

    category_df = pd.concat(
        [category_entry, category_df],
        ignore_index=True
    )

    category_df = category_df.drop_duplicates(
        subset=["jobtitle", "company", "jobdescription"]
    )

    category_df = category_df.head(jobs_per_category)

    if len(category_df) > 0:
        category_df["category"] = category
        selected_parts.append(category_df)

    print(category, "->", len(category_df))


# --------------------------------------------------
# 12. Combine all selected jobs
# --------------------------------------------------

if selected_parts:
    final_df = pd.concat(
        selected_parts,
        ignore_index=True
    )
else:
    final_df = pd.DataFrame()


# --------------------------------------------------
# 13. If more than 200, keep exactly 200
# --------------------------------------------------

final_df = final_df.drop_duplicates(
    subset=["jobtitle", "company", "jobdescription"]
)

final_df = final_df.head(200)


# --------------------------------------------------
# 14. Remove helper column
# --------------------------------------------------

if "combined_text" in final_df.columns:
    final_df = final_df.drop(columns=["combined_text"])


# --------------------------------------------------
# 15. Save final dataset
# --------------------------------------------------

final_df.to_csv(
    output_file,
    index=False
)

print("\n--------------------------------")
print("Final dataset created!")
print("--------------------------------")
print("Rows:", len(final_df))
print("Columns:", list(final_df.columns))
print("Saved to:", output_file)

print("\nCategory distribution:")
print(final_df["category"].value_counts())