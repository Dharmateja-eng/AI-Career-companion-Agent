import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pandas as pd

from agents.job_retrieval_agent import JobRetrievalAgent
from agents.job_matching_agent import JobMatchingAgent


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(PROJECT_ROOT, "data", "job_postings_clean.csv")


# ---------------------------------------------------------
# Sample student profiles
# ---------------------------------------------------------

students = [
    {
        "name": "Student 1 - Python AI Student",
        "skills": ["Python", "SQL", "Machine Learning", "Pandas", "NumPy", "Flask"],
        "education": "B.Tech CSE",
        "experience": "0 years",
        "projects": [
            "Machine Learning prediction project",
            "Python Flask web application"
        ],
        "certifications": ["Machine Learning", "Python"]
    },

    {
        "name": "Student 2 - Java Developer",
        "skills": ["Java", "SQL", "Spring Boot", "Git", "REST API"],
        "education": "B.Tech CSE",
        "experience": "1 year",
        "projects": [
            "Java Spring Boot application",
            "REST API project"
        ],
        "certifications": ["Java"]
    },

    {
        "name": "Student 3 - Web Developer",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "Git"],
        "education": "B.Tech CSE",
        "experience": "0 years",
        "projects": [
            "React frontend project",
            "Web development project"
        ],
        "certifications": ["Web Development"]
    },

    {
        "name": "Student 4 - Data and SQL Student",
        "skills": ["Python", "SQL", "MySQL", "Pandas", "NumPy", "Power BI"],
        "education": "B.Tech IT",
        "experience": "0 years",
        "projects": [
            "Data analysis project",
            "SQL database project"
        ],
        "certifications": ["Data Analysis"]
    },

    {
        "name": "Student 5 - Cloud DevOps Student",
        "skills": ["AWS", "Docker", "Kubernetes", "Linux", "Git", "DevOps"],
        "education": "B.Tech CSE",
        "experience": "1 year",
        "projects": [
            "AWS cloud project",
            "Docker deployment project"
        ],
        "certifications": ["Cloud Computing"]
    }
]


# ---------------------------------------------------------
# Expected job areas for evaluation
# ---------------------------------------------------------

expected_categories = {
    "Student 1 - Python AI Student": [
        "Data",
        "AI",
        "Analytics",
        "Software"
    ],

    "Student 2 - Java Developer": [
        "Software",
        "Development"
    ],

    "Student 3 - Web Developer": [
        "Web",
        "Development"
    ],

    "Student 4 - Data and SQL Student": [
        "Data",
        "Analytics",
        "Database",
        "SQL"
    ],

    "Student 5 - Cloud DevOps Student": [
        "Cloud",
        "DevOps"
    ]
}


# ---------------------------------------------------------
# Helper function
# ---------------------------------------------------------

def category_is_relevant(category, expected):
    """
    Check whether retrieved job category is reasonably
    related to the student's expected job area.
    """

    category = str(category).lower()

    for keyword in expected:
        if keyword.lower() in category:
            return True

    return False


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("MILESTONE 2.4 - RETRIEVAL AND MATCHING EVALUATION")
    print("=" * 70)

    # -----------------------------------------------------
    # Check dataset
    # -----------------------------------------------------

    if not os.path.exists(JOBS_FILE):
        print(f"ERROR: Job dataset not found: {JOBS_FILE}")
        sys.exit(1)

    jobs_df = pd.read_csv(JOBS_FILE)

    print(f"\nJob dataset loaded successfully")
    print(f"Total jobs available: {len(jobs_df)}")

    # -----------------------------------------------------
    # Initialize agents
    # -----------------------------------------------------

    print("\nInitializing agents...")

    retrieval_agent = JobRetrievalAgent()
    matching_agent = JobMatchingAgent()

    print("Retrieval Agent: OK")
    print("Matching Agent: OK")

    # -----------------------------------------------------
    # Evaluation counters
    # -----------------------------------------------------

    successful_students = 0
    relevant_retrievals = 0
    total_retrieved = 0
    correct_top_jobs = 0
    reasoning_available = 0
    skill_information_available = 0

    top_scores = []

    # -----------------------------------------------------
    # Evaluate every student
    # -----------------------------------------------------

    for student in students:

        name = student["name"]

        print("\n" + "=" * 70)
        print(name)
        print("=" * 70)

        try:

            # -------------------------------------------------
            # STEP 1 - Retrieval
            # -------------------------------------------------

            retrieved_jobs = retrieval_agent.retrieve_jobs(
                student,
                top_k_chunks=15,
                top_k_jobs=5
            )

            print("\nRetrieved Jobs:")

            if not retrieved_jobs:
                print("No jobs retrieved.")
                continue

            total_retrieved += len(retrieved_jobs)

            # -------------------------------------------------
            # Display retrieved jobs
            # -------------------------------------------------

            for i, job in enumerate(retrieved_jobs, start=1):

                print(
                    f"{i}. {job.get('job_title', 'Unknown')} | "
                    f"{job.get('company', 'Unknown')} | "
                    f"Retrieval Score: "
                    f"{job.get('retrieval_score', 0):.4f}"
                )

            # -------------------------------------------------
            # STEP 2 - Matching
            # -------------------------------------------------

            matching_result = matching_agent.match_jobs(
                student,
                retrieved_jobs
            )

            # Some implementations return a dictionary,
            # while others may return a list.
            if isinstance(matching_result, dict):
                matched_jobs = matching_result.get(
                    "matched_jobs",
                    []
                )
            else:
                matched_jobs = matching_result

            if not matched_jobs:
                print("\nNo matched jobs generated.")
                continue

            successful_students += 1

            # -------------------------------------------------
            # STEP 3 - Check matching results
            # -------------------------------------------------

            print("\nCompatibility Ranking:")

            previous_score = None
            ranking_correct = True

            for i, job in enumerate(matched_jobs, start=1):

                score = float(
                    job.get("compatibility_score", 0)
                )

                title = job.get(
                    "job_title",
                    "Unknown"
                )

                matching_skills = job.get(
                    "matching_skills",
                    []
                )

                missing_skills = job.get(
                    "missing_skills",
                    []
                )

                reasoning = job.get(
                    "reasoning",
                    ""
                )

                print(
                    f"{i}. {title} | "
                    f"{score:.2f}%"
                )

                print(
                    f"   Matching Skills: "
                    f"{matching_skills}"
                )

                print(
                    f"   Missing Skills: "
                    f"{missing_skills}"
                )

                # ---------------------------------------------
                # Check ranking consistency
                # ---------------------------------------------

                if previous_score is not None:
                    if score > previous_score:
                        ranking_correct = False

                previous_score = score

                # ---------------------------------------------
                # Check reasoning
                # ---------------------------------------------

                if reasoning and str(reasoning).strip():
                    reasoning_available += 1

                # ---------------------------------------------
                # Check skill information
                # ---------------------------------------------

                if matching_skills is not None:
                    skill_information_available += 1

            # -------------------------------------------------
            # Top job
            # -------------------------------------------------

            top_job = matched_jobs[0]

            top_title = top_job.get(
                "job_title",
                "Unknown"
            )

            top_score = float(
                top_job.get(
                    "compatibility_score",
                    0
                )
            )

            top_scores.append(top_score)

            print(
                f"\nTop Recommended Job: "
                f"{top_title}"
            )

            print(
                f"Top Compatibility Score: "
                f"{top_score:.2f}%"
            )

            # -------------------------------------------------
            # STEP 4 - Retrieval relevance
            # -------------------------------------------------

            expected = expected_categories.get(
                name,
                []
            )

            relevant_found = False

            for job in retrieved_jobs:

                category = job.get(
                    "category",
                    ""
                )

                title = job.get(
                    "job_title",
                    ""
                )

                if (
                    category_is_relevant(category, expected)
                    or category_is_relevant(title, expected)
                ):
                    relevant_found = True
                    break

            if relevant_found:

                relevant_retrievals += 1

                print(
                    "Retrieval Relevance: PASS"
                )

            else:

                print(
                    "Retrieval Relevance: CHECK"
                )

            # -------------------------------------------------
            # STEP 5 - Ranking consistency
            # -------------------------------------------------

            if ranking_correct:

                correct_top_jobs += 1

                print(
                    "Ranking Consistency: PASS"
                )

            else:

                print(
                    "Ranking Consistency: FAIL"
                )

        except Exception as e:

            print(
                f"\nEvaluation failed for {name}:"
            )

            print(e)

    # ---------------------------------------------------------
    # Final evaluation summary
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("MILESTONE 2.4 EVALUATION SUMMARY")
    print("=" * 70)

    total_students = len(students)

    print(
        f"\nStudent profiles tested: "
        f"{total_students}"
    )

    print(
        f"Successful evaluations: "
        f"{successful_students}/{total_students}"
    )

    # Retrieval relevance

    if total_students > 0:

        retrieval_percentage = (
            relevant_retrievals /
            total_students
        ) * 100

        print(
            f"Retrieval relevance: "
            f"{relevant_retrievals}/{total_students} "
            f"({retrieval_percentage:.2f}%)"
        )

    # Ranking

    if total_students > 0:

        ranking_percentage = (
            correct_top_jobs /
            total_students
        ) * 100

        print(
            f"Ranking consistency: "
            f"{correct_top_jobs}/{total_students} "
            f"({ranking_percentage:.2f}%)"
        )

    # Average score

    if top_scores:

        average_score = (
            sum(top_scores) /
            len(top_scores)
        )

        print(
            f"Average top-job compatibility: "
            f"{average_score:.2f}%"
        )

    # Retrieved jobs

    print(
        f"Total jobs retrieved: "
        f"{total_retrieved}"
    )

    # Reasoning

    print(
        f"Results with reasoning: "
        f"{reasoning_available}"
    )

    # Skill information

    print(
        f"Results with skill information: "
        f"{skill_information_available}"
    )

    # ---------------------------------------------------------
    # Pipeline status
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("M2 PIPELINE STATUS")
    print("=" * 70)

    print("""
Student Profile
      ↓
Candidate Query
      ↓
Gemini Embedding
      ↓
FAISS Semantic Retrieval
      ↓
Top-K Job Retrieval
      ↓
Job-Resume Matching Agent
      ↓
Skill Matching
      ↓
Education Matching
      ↓
Experience Matching
      ↓
Compatibility Score
      ↓
Ranked Job Recommendations
""")

    print("=" * 70)
    print("MILESTONE 2.4 EVALUATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()