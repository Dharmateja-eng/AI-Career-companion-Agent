import sys
import os
import json

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from dotenv import load_dotenv
from google import genai

from agents.m3_resume_cover_letter_agent import (
    M3ResumeCoverLetterAgent
)


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


candidate_profile = {
    "name": "Test Student",

    "education": (
        "B.Tech Artificial Intelligence and "
        "Machine Learning"
    ),

    "skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "Git"
    ],

    "projects": [
        "AI Career Companion",
        "House Price Prediction using Flask"
    ],

    "experience": [],

    "certifications": [
        "Machine Learning with Python"
    ]
}


job = {
    "job_id": "TEST001",

    "jobtitle": "Python Developer Intern",

    "company": "Test Company",

    "jobdescription": (
        "Looking for a Python intern to work on "
        "backend applications and REST APIs."
    ),

    "skills": (
        "Python, Flask, REST API, SQL, Git"
    ),

    "experience": "Fresher",

    "education": "B.Tech"
}


print("Starting M3.2 Resume & Cover Letter Agent test...")

agent = M3ResumeCoverLetterAgent(client)

result = agent.customize(
    candidate_profile,
    job
)

print("\nM3.2 TEST RESULT:")
print(
    json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    )
)

print("\nM3.2 TEST COMPLETED.")