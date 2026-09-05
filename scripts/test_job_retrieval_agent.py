from agents.job_retrieval_agent import JobRetrievalAgent


candidate_profile = {

    "name": "Test Student",

    "skills": [
        "Python",
        "Flask",
        "SQL",
        "Java",
        "HTML",
        "CSS",
        "Git"
    ],

    "education": [
        "B.Tech Computer Science"
    ],

    "experience": [],

    "projects": [
        "Python Flask Web Application"
    ],

    "certifications": []

}


retrieval_agent = JobRetrievalAgent()


jobs = retrieval_agent.retrieve_jobs(
    candidate_profile,
    top_k_chunks=15,
    top_k_jobs=5
)


print("\n===== RETRIEVED JOBS =====\n")


for rank, job in enumerate(
    jobs,
    start=1
):

    print(
        f"Rank: {rank}"
    )

    print(
        f"Retrieval Score: {job['retrieval_score']}"
    )

    print(
        f"Job Title: {job['job_title']}"
    )

    print(
        f"Company: {job['company']}"
    )

    print(
        f"Category: {job['category']}"
    )

    print(
        f"Job ID: {job['jobid']}"
    )

    print(
        f"Skills: {job['skills']}"
    )

    print("-" * 60)