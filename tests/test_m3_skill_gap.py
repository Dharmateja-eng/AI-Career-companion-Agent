import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
import os
import json
from dotenv import load_dotenv
from google import genai

from agents.m3_skill_gap_agent import M3SkillGapAgent


# Load environment variables
load_dotenv()

# Create Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ---------------------------------------
# Sample student profile
# ---------------------------------------

candidate_profile = {
    "name": "Sample Student",
    "education": "B.Tech in Artificial Intelligence and Machine Learning",
    "experience": "No professional experience",
    "skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "Git"
    ],
    "projects": [
        "House Price Prediction using Machine Learning",
        "AI Career Companion"
    ],
    "certifications": [
        "Machine Learning certification"
    ]
}


# ---------------------------------------
# Sample selected internship/job
# ---------------------------------------

job = {
    "job_id": "TEST001",
    "job_title": "Python Developer Intern",
    "company": "Sample Tech Company",
    "category": "Software Development",
    "skills": "Python, Flask, SQL, Git, REST API",
    "experience": "0-1 years",
    "education": "Bachelor's degree in Computer Science or related field",
    "description": """
    Looking for a Python Developer Intern who can work
    with Python applications, Flask, SQL databases,
    REST APIs and Git.
    """,
    "location": "India",
    "industry": "Information Technology"
}


# ---------------------------------------
# Run M3.1 Skill Gap Agent
# ---------------------------------------

agent = M3SkillGapAgent(client)

result = agent.analyze(
    candidate_profile,
    job
)


# ---------------------------------------
# Display result
# ---------------------------------------

print("\n======================================")
print("M3.1 SKILL GAP ANALYSIS RESULT")
print("======================================\n")

print(
    json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    )
)