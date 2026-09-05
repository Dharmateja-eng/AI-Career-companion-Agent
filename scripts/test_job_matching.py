from agents.job_matching_agent import JobMatchingAgent

candidate_profile = {
    "name": "Test Student",
    "education": ["B.Tech Computer Science"],
    "skills": [
        "Python",
        "Flask",
        "SQL",
        "Java",
        "HTML",
        "CSS",
        "Git"
    ],
    "experience": [],
    "projects": [
        "Python Flask Web Application"
    ],
    "certifications": [],
    "achievements": [],
    "languages": ["English"]
}

retrieved_jobs = [
    {
        "jobid": "TEST001",
        "job_title": "Python Developer",
        "company": "Example Company",
        "skills": "Python, Flask, SQL, Git",
        "experience": "0-2 years",
        "education": "B.Tech"
    },
    {
        "jobid": "TEST002",
        "job_title": "Java Developer",
        "company": "Example Tech",
        "skills": "Java, Spring, SQL",
        "experience": "0-2 years",
        "education": "B.Tech"
    }
]

agent = JobMatchingAgent()

result = agent.match_jobs(
    candidate_profile,
    retrieved_jobs
)

print("\n===== JOB MATCHING RESULTS =====\n")
print(result)