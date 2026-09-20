import os
import sys

from dotenv import load_dotenv


# Allow imports from the project root
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)


# Load environment variables from .env
load_dotenv()

from agents.m3_career_assistant_agent import (
    M3CareerAssistantAgent
)

from google import genai


# --------------------------------------------------
# GEMINI CLIENT
# --------------------------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# --------------------------------------------------
# CREATE AGENT
# --------------------------------------------------

agent = M3CareerAssistantAgent(
    client
)


# --------------------------------------------------
# SAMPLE STUDENT PROFILE
# --------------------------------------------------

student_profile = {

    "name": "Test Student",

    "education": [
        "B.Tech Artificial Intelligence and Machine Learning"
    ],

    "skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "Git"
    ],

    "projects": [
        "House Price Prediction using Flask",
        "AI Career Companion"
    ],

    "certifications": [
        "Machine Learning with Python"
    ]

}


# --------------------------------------------------
# SAMPLE MATCHED JOBS
# --------------------------------------------------

matched_jobs = [

    {
        "job_id": "TEST001",
        "title": "Python Developer Intern",
        "company": "Test Company",
        "compatibility_score": 82,
        "matching_skills": [
            "Python",
            "SQL",
            "Git"
        ],
        "missing_skills": [
            "Flask",
            "REST API"
        ]
    }

]


# --------------------------------------------------
# SAMPLE SKILL GAP
# --------------------------------------------------

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

    "recommendations": [
        "Build a small Flask REST API.",
        "Practice CRUD operations using SQLAlchemy."
    ]

}


# --------------------------------------------------
# SAMPLE INTERVIEW PREPARATION
# --------------------------------------------------

interview_preparation = {

    "job_id": "TEST001",

    "job_title": "Python Developer Intern",

    "revision_topics": [
        "Flask routing",
        "REST APIs",
        "SQLAlchemy",
        "Git"
    ],

    "technical_questions": [
        "Explain GET and POST requests.",
        "How does Flask routing work?"
    ]

}


# --------------------------------------------------
# SAMPLE CONVERSATION
# --------------------------------------------------

conversation_history = [

    {
        "role": "user",
        "message": "What skills do I already have?"
    },

    {
        "role": "assistant",
        "message": (
            "You currently have Python, SQL, "
            "Machine Learning and Git in your profile."
        )
    }

]


# --------------------------------------------------
# TEST QUESTION
# --------------------------------------------------

question = (
    "What should I learn first if I want to apply "
    "for the Python Developer internship?"
)


# --------------------------------------------------
# RUN AGENT
# --------------------------------------------------

answer = agent.respond(

    student_profile=student_profile,

    user_message=question,

    matched_jobs=matched_jobs,

    skill_gap=skill_gap,

    interview_preparation=interview_preparation,

    conversation_history=conversation_history

)


# --------------------------------------------------
# DISPLAY RESULT
# --------------------------------------------------

print()
print("=" * 60)
print("M3.4 CAREER ASSISTANT TEST RESULT")
print("=" * 60)
print()

print(answer)

print()
print("=" * 60)
print("M3.4 TEST COMPLETED")
print("=" * 60)