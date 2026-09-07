import os
import json
import importlib.util


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

EVALUATION_DIR = os.path.join(
    BASE_DIR,
    "data",
    "evaluation"
)

OUTPUT_FILE = os.path.join(
    EVALUATION_DIR,
    "evaluation_results.json"
)


# ---------------------------------------------------------
# Load agent classes dynamically
# ---------------------------------------------------------

def load_class(filename, class_name):

    for root, dirs, files in os.walk(BASE_DIR):

        if filename in files:

            file_path = os.path.join(root, filename)

            spec = importlib.util.spec_from_file_location(
                class_name,
                file_path
            )

            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

            return getattr(module, class_name)

    raise FileNotFoundError(
        f"{filename} was not found in the project."
    )


JobRetrievalAgent = load_class(
    "job_retrieval_agent.py",
    "JobRetrievalAgent"
)

JobMatchingAgent = load_class(
    "job_matching_agent.py",
    "JobMatchingAgent"
)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def normalize(text):
    return str(text).lower().strip()


def check_category_match(jobs, expected_categories):

    expected = {
        normalize(category)
        for category in expected_categories
    }

    retrieved_categories = [
        normalize(job.get("category", ""))
        for job in jobs
    ]

    matches = [
        category
        for category in retrieved_categories
        if category in expected
    ]

    return len(matches) > 0, matches


def check_role_match(jobs, expected_roles):

    expected_roles = [
        normalize(role)
        for role in expected_roles
    ]

    matched_roles = []

    for job in jobs:

        title = normalize(
            job.get("job_title", "")
        )

        for role in expected_roles:

            if role in title or title in role:

                matched_roles.append(
                    job.get("job_title", "")
                )

                break

    return len(matched_roles) > 0, matched_roles


def check_skill_consistency(
    candidate_profile,
    matched_jobs
):

    candidate_skills = {
        normalize(skill)
        for skill in candidate_profile.get(
            "skills",
            []
        )
    }

    valid_matching_skills = 0
    invalid_matching_skills = 0

    invalid_skills = []

    for job in matched_jobs:

        matching_skills = job.get(
            "matching_skills",
            []
        )

        for skill in matching_skills:

            if normalize(skill) in candidate_skills:

                valid_matching_skills += 1

            else:

                invalid_matching_skills += 1

                invalid_skills.append(skill)

    return {
        "valid_matching_skills": valid_matching_skills,
        "invalid_matching_skills": invalid_matching_skills,
        "invalid_skills": invalid_skills
    }


def check_score_consistency(matched_jobs):

    scores = []

    for job in matched_jobs:

        score = job.get(
            "compatibility_score"
        )

        if isinstance(score, (int, float)):

            scores.append(score)

    valid_range = all(
        0 <= score <= 100
        for score in scores
    )

    sorted_descending = (
        scores == sorted(
            scores,
            reverse=True
        )
    )

    return {
        "scores": scores,
        "valid_range": valid_range,
        "sorted_descending": sorted_descending
    }


def check_reasoning(matched_jobs):

    jobs_with_reasoning = 0

    for job in matched_jobs:

        reasoning = job.get(
            "reasoning",
            ""
        )

        if isinstance(reasoning, str) and reasoning.strip():

            jobs_with_reasoning += 1

    return {
        "jobs_with_reasoning": jobs_with_reasoning,
        "total_jobs": len(matched_jobs)
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("MILESTONE 2 - RAG & JOB MATCHING EVALUATION")
    print("=" * 60)

    retrieval_agent = JobRetrievalAgent()
    matching_agent = JobMatchingAgent()

    expected_file = os.path.join(
        EVALUATION_DIR,
        "expected_results.json"
    )

    with open(
        expected_file,
        "r",
        encoding="utf-8"
    ) as file:

        expected_results = json.load(file)

    profile_files = [
        file
        for file in os.listdir(EVALUATION_DIR)
        if file.endswith(".json")
        and file != "expected_results.json"
        and file != "evaluation_results.json"
    ]

    all_results = []

    for profile_file in sorted(profile_files):

        profile_path = os.path.join(
            EVALUATION_DIR,
            profile_file
        )

        with open(
            profile_path,
            "r",
            encoding="utf-8"
        ) as file:

            candidate_profile = json.load(file)

        student_name = candidate_profile.get(
            "name",
            profile_file
        )

        print()
        print("-" * 60)
        print(f"Evaluating: {student_name}")
        print("-" * 60)

        # -------------------------------------------------
        # 1. RAG Retrieval
        # -------------------------------------------------

        retrieved_jobs = retrieval_agent.retrieve_jobs(
            candidate_profile,
            top_k_chunks=15,
            top_k_jobs=5
        )

        print(
            f"Retrieved jobs: {len(retrieved_jobs)}"
        )

        # -------------------------------------------------
        # 2. Job Matching
        # -------------------------------------------------

        matching_result = matching_agent.match_jobs(
            candidate_profile,
            retrieved_jobs
        )

        matched_jobs = matching_result.get(
            "matched_jobs",
            []
        )

        print(
            f"Matched jobs: {len(matched_jobs)}"
        )

        # -------------------------------------------------
        # 3. Manual expected results
        # -------------------------------------------------

        manual = expected_results.get(
            student_name,
            {}
        )

        expected_categories = manual.get(
            "expected_categories",
            []
        )

        expected_roles = manual.get(
            "expected_roles",
            []
        )

        # -------------------------------------------------
        # 4. Evaluation metrics
        # -------------------------------------------------

        category_match, category_matches = (
            check_category_match(
                retrieved_jobs,
                expected_categories
            )
        )

        role_match, role_matches = (
            check_role_match(
                matched_jobs,
                expected_roles
            )
        )

        skill_consistency = (
            check_skill_consistency(
                candidate_profile,
                matched_jobs
            )
        )

        score_consistency = (
            check_score_consistency(
                matched_jobs
            )
        )

        reasoning_quality = (
            check_reasoning(
                matched_jobs
            )
        )

        # -------------------------------------------------
        # 5. Store result
        # -------------------------------------------------

        result = {
            "student": student_name,

            "manual_expectation": {
                "expected_categories": expected_categories,
                "expected_roles": expected_roles
            },

            "retrieval_evaluation": {
                "retrieved_job_count": len(
                    retrieved_jobs
                ),
                "category_match": category_match,
                "matching_categories": category_matches,
                "retrieved_jobs": retrieved_jobs
            },

            "matching_evaluation": {
                "role_match": role_match,
                "matching_expected_roles": role_matches,
                "matched_jobs": matched_jobs
            },

            "skill_matching_evaluation": skill_consistency,

            "score_consistency_evaluation": score_consistency,

            "reasoning_evaluation": reasoning_quality
        }

        all_results.append(result)

        # -------------------------------------------------
        # Console summary
        # -------------------------------------------------

        print(
            f"Category match: "
            f"{'PASS' if category_match else 'FAIL'}"
        )

        print(
            f"Expected role match: "
            f"{'PASS' if role_match else 'FAIL'}"
        )

        print(
            f"Score range valid: "
            f"{'PASS' if score_consistency['valid_range'] else 'FAIL'}"
        )

        print(
            f"Score ordering valid: "
            f"{'PASS' if score_consistency['sorted_descending'] else 'FAIL'}"
        )

        print(
            f"Reasoning present: "
            f"{reasoning_quality['jobs_with_reasoning']}/"
            f"{reasoning_quality['total_jobs']}"
        )

    # -----------------------------------------------------
    # Save complete evaluation results
    # -----------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_results,
            file,
            indent=4
        )

    print()
    print("=" * 60)
    print("EVALUATION COMPLETED")
    print("=" * 60)

    print(
        f"Results saved to:\n{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()