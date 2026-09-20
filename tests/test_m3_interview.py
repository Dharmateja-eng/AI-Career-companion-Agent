import sys
import os
import json

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from dotenv import load_dotenv
from google import genai

from agents.m3_interview_agent import M3InterviewAgent


load_dotenv()


print("Starting M3.3 Interview Preparation Agent test...")


# Create Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# --------------------------------
# SAMPLE STUDENT PROFILE
# --------------------------------

candidate_profile = {

    "name": "Test Student",

    "education": [
        "B.Tech Artificial Intelligence and Machine Learning"
    ],

    "skills": [
        "Python",
        "SQL",
        "Git"
    ],

    "projects": [
        "House Price Prediction using Flask",
        "AI Career Companion"
    ],

    "experience": [],

    "certifications": [
        "Machine Learning with Python"
    ]
}


# --------------------------------
# SAMPLE SELECTED JOB
# --------------------------------

selected_job = {

    "job_id": "TEST001",

    "job_title": "Python Developer Intern",

    "company": "Test Company",

    "skills": [
        "Python",
        "Flask",
        "REST API",
        "SQL",
        "Git"
    ],

    "experience": "Fresher",

    "education": "B.Tech / BE",

    "jobdescription": """
    Develop backend applications using Python and Flask.
    Work with REST APIs and databases.
    Collaborate with the development team.
    """
}


# --------------------------------
# SAMPLE SKILL GAP
# --------------------------------

skill_gap = {

    "job_id": "TEST001",

    "job_title": "Python Developer Intern",

    "critical_missing_skills": [
        "Flask",
        "REST API"
    ],

    "partially_demonstrated_skills": [
        "Python",
        "SQL",
        "Git"
    ],

    "preferred_skills": [],

    "experience_gaps": [],

    "qualification_gaps": [],

    "gap_explanations": [

        "Flask is directly relevant to the backend responsibilities.",

        "REST API knowledge is relevant to the job's API development work."

    ],

    "recommendations": [

        "Practice building Flask REST APIs.",

        "Review SQL database integration with Flask."

    ]
}


# --------------------------------
# CREATE AGENT
# --------------------------------

agent = M3InterviewAgent(client)


# --------------------------------
# GENERATE INTERVIEW PREPARATION
# --------------------------------

result = agent.prepare(

    candidate_profile,

    selected_job,

    skill_gap

)


# --------------------------------
# DISPLAY RESULT
# --------------------------------

print("\nM3.3 TEST RESULT:")

print(
    json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    )
)


print("\nM3.3 TEST COMPLETED.")