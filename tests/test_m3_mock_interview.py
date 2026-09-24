import os
import json
import sys
from dotenv import load_dotenv
from google import genai

# Allow importing agents from the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.m3_mock_interview_agent import M3MockInterviewAgent


# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")


# Create Gemini client
client = genai.Client(api_key=api_key)

# Create Mock Interview Agent
agent = M3MockInterviewAgent(client)


# --------------------------------------------------
# Sample Student Profile
# --------------------------------------------------

candidate_profile = {
    "name": "Test Student",
    "education": "B.Tech Artificial Intelligence and Machine Learning",
    "skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "Git"
    ],
    "projects": [
        {
            "name": "House Price Prediction",
            "technologies": [
                "Python",
                "Machine Learning",
                "Flask"
            ]
        },
        {
            "name": "AI Career Companion",
            "technologies": [
                "Python",
                "Flask",
                "Gemini",
                "FAISS"
            ]
        }
    ],
    "certifications": [
        "Machine Learning Certification"
    ],
    "experience": []
}


# --------------------------------------------------
# Sample Selected Job
# --------------------------------------------------

job = {
    "job_id": "TEST001",
    "job_title": "Python Developer Intern",
    "company": "Test Company",
    "category": "Software Development",
    "skills": [
        "Python",
        "Flask",
        "SQL",
        "Git"
    ],
    "experience": "Fresher",
    "education": "B.Tech"
}


# --------------------------------------------------
# Sample Interview Context
# --------------------------------------------------

interview_context = {
    "skill_gaps": [
        "REST API",
        "Advanced Flask"
    ],
    "revision_topics": [
        "Flask",
        "REST API",
        "SQL",
        "Git"
    ]
}


print("=" * 60)
print("M3 MOCK INTERVIEW AGENT TEST")
print("=" * 60)


# --------------------------------------------------
# 1. Generate Question
# --------------------------------------------------

print("\n1. GENERATING INTERVIEW QUESTION...")
print("-" * 60)

question_result = agent.generate_question(
    candidate_profile=candidate_profile,
    job=job,
    interview_context=interview_context,
    previous_questions=[]
)

print(json.dumps(question_result, indent=4))


question = question_result.get("question")

if not question:
    raise ValueError("Question was not generated")

print("\nGenerated Question:")
print(question)


# --------------------------------------------------
# 2. Evaluate Sample Answer
# --------------------------------------------------

sample_answer = """
I used Flask in my House Price Prediction project to create
a web application. The user enters the required house details,
and the Flask application sends those inputs to the trained
machine learning model. The model predicts the house price
and the result is displayed on the web page.
"""


print("\n\n2. EVALUATING SAMPLE ANSWER...")
print("-" * 60)

evaluation_result = agent.evaluate_answer(
    candidate_profile=candidate_profile,
    job=job,
    question=question,
    answer=sample_answer,
    interview_context=interview_context
)

print(json.dumps(evaluation_result, indent=4))


# Check score
score = evaluation_result.get("score")

if score is None:
    raise ValueError("Evaluation score was not generated")

print("\nEvaluation Score:")
print(score)


# --------------------------------------------------
# 3. Generate Final Summary
# --------------------------------------------------

interview_results = [
    {
        "question": question,
        "answer": sample_answer,
        "evaluation": evaluation_result
    }
]


print("\n\n3. GENERATING FINAL INTERVIEW SUMMARY...")
print("-" * 60)

summary_result = agent.generate_final_summary(
    candidate_profile=candidate_profile,
    job=job,
    interview_results=interview_results
)

print(json.dumps(summary_result, indent=4))


# Check average score
average_score = summary_result.get("average_score")

if average_score is None:
    raise ValueError("Average score was not generated")

print("\nAverage Score:")
print(average_score)


print("\n" + "=" * 60)
print("M3 MOCK INTERVIEW AGENT TEST PASSED")
print("=" * 60)