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

            file_path = os.path.join(
                root,
                filename
            )

            spec = importlib.util.spec_from_file_location(
                class_name,
                file_path
            )

            module = importlib.util.module_from_spec(
                spec
            )

            spec.loader.exec_module(module)

            return getattr(
                module,
                class_name
            )

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


# ---------------------------------------------------------
# Category relevance evaluation
# ---------------------------------------------------------

def check_category_relevance(
    jobs,
    expected_categories
):

    expected = {
        normalize(category)
        for category in expected_categories
    }

    retrieved_categories = [
        normalize(
            job.get("category", "")
        )
        for job in jobs
    ]

    matching_categories = [
        category
        for category in retrieved_categories
        if category in expected
    ]

    # Hit@5:
    # At least one expected category appears
    hit_at_5 = len(matching_categories) > 0

    # Precision@5:
    # Percentage of retrieved jobs belonging
    # to an expected category
    total_jobs = len(retrieved_categories)

    if total_jobs > 0:
        precision_at_5 = (
            len(matching_categories)
            / total_jobs
        )
    else:
        precision_at_5 = 0.0

    # Top-1 category relevance
    top_1_match = False

    if retrieved_categories:
        top_1_match = (
            retrieved_categories[0]
            in expected
        )

    return {
        "hit_at_5": hit_at_5,

        "precision_at_5":
            round(
                precision_at_5,
                2
            ),

        "top_1_match":
            top_1_match,

        "matching_categories":
            matching_categories,

        "retrieved_categories":
            retrieved_categories
    }


# ---------------------------------------------------------
# Role relevance evaluation
# ---------------------------------------------------------

def check_role_relevance(
    jobs,
    expected_roles
):

    expected_roles = [
        normalize(role)
        for role in expected_roles
    ]

    relevant_jobs = []

    role_keywords = {

        "python developer": [
            "python",
            "software engineer",
            "software developer",
            "application developer"
        ],

        "java developer": [
            "java",
            "software engineer",
            "software developer",
            "application developer"
        ],

        "web developer": [
            "web",
            "frontend",
            "full stack",
            "software developer",
            "software engineer"
        ],

        "frontend developer": [
            "frontend",
            "web",
            "react",
            "ui"
        ],

        "software developer": [
            "software",
            "developer",
            "engineer",
            "application"
        ],

        "machine learning engineer": [
            "machine learning",
            "ml",
            "data",
            "analytics",
            "python"
        ],

        "data analyst": [
            "data",
            "analytics",
            "analyst",
            "business intelligence"
        ],

        "cloud engineer": [
            "cloud",
            "aws",
            "azure",
            "devops"
        ],

        "devops engineer": [
            "devops",
            "cloud",
            "aws",
            "azure",
            "ci/cd"
        ]
    }

    for job in jobs:

        title = normalize(
            job.get(
                "job_title",
                ""
            )
        )

        is_relevant = False

        for role in expected_roles:

            # Direct title match
            if (
                role in title
                or title in role
            ):
                is_relevant = True
                break

            # Related role keywords
            keywords = role_keywords.get(
                role,
                []
            )

            if any(
                keyword in title
                for keyword in keywords
            ):
                is_relevant = True
                break

        if is_relevant:

            relevant_jobs.append(
                job.get(
                    "job_title",
                    ""
                )
            )

    total_jobs = len(jobs)

    role_precision = (
        len(relevant_jobs) / total_jobs
        if total_jobs > 0
        else 0.0
    )

    return {

        "relevant":
            len(relevant_jobs) > 0,

        "relevant_job_titles":
            relevant_jobs,

        "role_precision_at_5":
            round(
                role_precision,
                2
            )
    }


# ---------------------------------------------------------
# Skill consistency evaluation
# ---------------------------------------------------------

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

                invalid_skills.append(
                    skill
                )

    total = (
        valid_matching_skills
        + invalid_matching_skills
    )

    consistency_pass = (
        invalid_matching_skills == 0
    )

    return {

        "valid_matching_skills":
            valid_matching_skills,

        "invalid_matching_skills":
            invalid_matching_skills,

        "invalid_skills":
            invalid_skills,

        "total_matching_skills":
            total,

        "consistency_pass":
            consistency_pass
    }


# ---------------------------------------------------------
# Score consistency evaluation
# ---------------------------------------------------------

def check_score_consistency(
    matched_jobs
):

    scores = []

    for job in matched_jobs:

        score = job.get(
            "compatibility_score"
        )

        if isinstance(
            score,
            (int, float)
        ):

            scores.append(score)

    valid_range = (
        len(scores) == len(matched_jobs)
        and all(
            0 <= score <= 100
            for score in scores
        )
    )

    sorted_descending = (
        scores
        == sorted(
            scores,
            reverse=True
        )
    )

    return {

        "scores":
            scores,

        "valid_range":
            valid_range,

        "sorted_descending":
            sorted_descending
    }


# ---------------------------------------------------------
# Reasoning quality evaluation
# ---------------------------------------------------------

def check_reasoning(
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

    results = []

    for job in matched_jobs:

        reasoning = job.get(
            "reasoning",
            ""
        )

        matching_skills = job.get(
            "matching_skills",
            []
        )

        missing_skills = job.get(
            "missing_skills",
            []
        )

        reasoning_text = normalize(
            reasoning
        )

        has_reasoning = bool(
            reasoning_text
        )

        mentions_candidate_skill = any(
            normalize(skill)
            in reasoning_text
            for skill in candidate_skills
        )

        mentions_matching_skill = any(
            normalize(skill)
            in reasoning_text
            for skill in matching_skills
        )

        mentions_missing_skill = any(
            normalize(skill)
            in reasoning_text
            for skill in missing_skills
        )

        evidence_count = sum([
            mentions_candidate_skill,
            mentions_matching_skill,
            mentions_missing_skill
        ])

        quality_pass = (
            has_reasoning
            and evidence_count >= 1
        )

        results.append({

            "job_title":
                job.get(
                    "job_title",
                    ""
                ),

            "reasoning_present":
                has_reasoning,

            "mentions_candidate_skill":
                mentions_candidate_skill,

            "mentions_matching_skill":
                mentions_matching_skill,

            "mentions_missing_skill":
                mentions_missing_skill,

            "quality_pass":
                quality_pass
        })

    passed = sum(
        1
        for result in results
        if result["quality_pass"]
    )

    total_jobs = len(matched_jobs)

    reasoning_percentage = (
        (passed / total_jobs) * 100
        if total_jobs > 0
        else 0
    )

    return {

        "jobs_with_reasoning":
            sum(
                1
                for result in results
                if result["reasoning_present"]
            ),

        "quality_passed_jobs":
            passed,

        "total_jobs":
            total_jobs,

        "quality_percentage":
            round(
                reasoning_percentage,
                2
            ),

        "details":
            results
    }


# ---------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print(
        "MILESTONE 2 - RAG & JOB MATCHING EVALUATION"
    )
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
        for file in os.listdir(
            EVALUATION_DIR
        )
        if file.endswith(".json")
        and file != "expected_results.json"
        and file != "evaluation_results.json"
    ]

    all_results = []

    # -----------------------------------------------------
    # Overall counters
    # -----------------------------------------------------

    total_students = 0

    category_hit_passes = 0
    category_top1_passes = 0

    role_passes = 0

    score_range_passes = 0
    score_order_passes = 0

    skill_consistency_passes = 0

    students_with_all_reasoning_passed = 0

    total_matched_jobs = 0
    total_reasoning_jobs = 0

    total_reasoning_quality_passed = 0
    total_reasoning_evaluated_jobs = 0

    total_category_precision = 0.0
    total_role_precision = 0.0

    # -----------------------------------------------------
    # Evaluate every student
    # -----------------------------------------------------

    for profile_file in sorted(
        profile_files
    ):

        profile_path = os.path.join(
            EVALUATION_DIR,
            profile_file
        )

        with open(
            profile_path,
            "r",
            encoding="utf-8"
        ) as file:

            candidate_profile = json.load(
                file
            )

        student_name = candidate_profile.get(
            "name",
            profile_file
        )

        total_students += 1

        print()
        print("-" * 60)
        print(
            f"Evaluating: {student_name}"
        )
        print("-" * 60)

        # -------------------------------------------------
        # 1. RAG Retrieval
        # -------------------------------------------------

        retrieved_jobs = (
            retrieval_agent.retrieve_jobs(
                candidate_profile,
                top_k_chunks=15,
                top_k_jobs=5
            )
        )

        print(
            f"Retrieved jobs: "
            f"{len(retrieved_jobs)}"
        )

        # -------------------------------------------------
        # 2. Job Matching
        # -------------------------------------------------

        matching_result = (
            matching_agent.match_jobs(
                candidate_profile,
                retrieved_jobs
            )
        )

        matched_jobs = (
            matching_result.get(
                "matched_jobs",
                []
            )
        )

        total_matched_jobs += len(
            matched_jobs
        )

        print(
            f"Matched jobs: "
            f"{len(matched_jobs)}"
        )

        # -------------------------------------------------
        # 3. Manual expected results
        # -------------------------------------------------

        manual = expected_results.get(
            student_name,
            {}
        )

        expected_categories = (
            manual.get(
                "expected_categories",
                []
            )
        )

        expected_roles = (
            manual.get(
                "expected_roles",
                []
            )
        )

        # -------------------------------------------------
        # 4. Category evaluation
        # -------------------------------------------------

        category_evaluation = (
            check_category_relevance(
                retrieved_jobs,
                expected_categories
            )
        )

        category_hit = (
            category_evaluation[
                "hit_at_5"
            ]
        )

        category_top1 = (
            category_evaluation[
                "top_1_match"
            ]
        )

        total_category_precision += (
            category_evaluation[
                "precision_at_5"
            ]
        )

        # -------------------------------------------------
        # 5. Role evaluation
        # -------------------------------------------------

        role_evaluation = (
            check_role_relevance(
                matched_jobs,
                expected_roles
            )
        )

        role_match = (
            role_evaluation[
                "relevant"
            ]
        )

        total_role_precision += (
            role_evaluation[
                "role_precision_at_5"
            ]
        )

        # -------------------------------------------------
        # 6. Skill consistency
        # -------------------------------------------------

        skill_consistency = (
            check_skill_consistency(
                candidate_profile,
                matched_jobs
            )
        )

        # -------------------------------------------------
        # 7. Score consistency
        # -------------------------------------------------

        score_consistency = (
            check_score_consistency(
                matched_jobs
            )
        )

        # -------------------------------------------------
        # 8. Reasoning quality
        # -------------------------------------------------

        reasoning_quality = (
            check_reasoning(
                candidate_profile,
                matched_jobs
            )
        )

        # -------------------------------------------------
        # 9. Update overall counters
        # -------------------------------------------------

        if category_hit:
            category_hit_passes += 1

        if category_top1:
            category_top1_passes += 1

        if role_match:
            role_passes += 1

        if score_consistency[
            "valid_range"
        ]:
            score_range_passes += 1

        if score_consistency[
            "sorted_descending"
        ]:
            score_order_passes += 1

        if skill_consistency[
            "consistency_pass"
        ]:
            skill_consistency_passes += 1

        # Student-level reasoning:
        # Did ALL matched jobs pass?
        if (
            reasoning_quality[
                "quality_passed_jobs"
            ]
            == reasoning_quality[
                "total_jobs"
            ]
            and reasoning_quality[
                "total_jobs"
            ] > 0
        ):

            students_with_all_reasoning_passed += 1

        # Job-level reasoning
        total_reasoning_quality_passed += (
            reasoning_quality[
                "quality_passed_jobs"
            ]
        )

        total_reasoning_evaluated_jobs += (
            reasoning_quality[
                "total_jobs"
            ]
        )

        total_reasoning_jobs += (
            reasoning_quality[
                "jobs_with_reasoning"
            ]
        )

        # -------------------------------------------------
        # 10. Store detailed result
        # -------------------------------------------------

        result = {

            "student":
                student_name,

            "manual_expectation": {

                "expected_categories":
                    expected_categories,

                "expected_roles":
                    expected_roles
            },

            "retrieval_evaluation": {

                "retrieved_job_count":
                    len(retrieved_jobs),

                "category_hit_at_5":
                    category_evaluation[
                        "hit_at_5"
                    ],

                "category_precision_at_5":
                    category_evaluation[
                        "precision_at_5"
                    ],

                "top_1_category_match":
                    category_evaluation[
                        "top_1_match"
                    ],

                "matching_categories":
                    category_evaluation[
                        "matching_categories"
                    ],

                "retrieved_categories":
                    category_evaluation[
                        "retrieved_categories"
                    ],

                "retrieved_jobs":
                    retrieved_jobs
            },

            "matching_evaluation": {

                "role_match":
                    role_match,

                "role_precision_at_5":
                    role_evaluation[
                        "role_precision_at_5"
                    ],

                "relevant_job_titles":
                    role_evaluation[
                        "relevant_job_titles"
                    ],

                "matched_jobs":
                    matched_jobs
            },

            "skill_matching_evaluation":
                skill_consistency,

            "score_consistency_evaluation":
                score_consistency,

            "reasoning_evaluation":
                reasoning_quality
        }

        all_results.append(
            result
        )

        # -------------------------------------------------
        # 11. Student console summary
        # -------------------------------------------------

        print(
            f"Category Hit@5: "
            f"{'PASS' if category_hit else 'FAIL'}"
        )

        print(
            f"Category Precision@5: "
            f"{category_evaluation['precision_at_5'] * 100:.0f}%"
        )

        print(
            f"Top-1 Category Relevance: "
            f"{'PASS' if category_top1 else 'FAIL'}"
        )

        print(
            f"Role relevance: "
            f"{'PASS' if role_match else 'FAIL'}"
        )

        print(
            f"Skill consistency: "
            f"{'PASS' if skill_consistency['consistency_pass'] else 'FAIL'}"
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
            f"Reasoning quality: "
            f"{reasoning_quality['quality_passed_jobs']}/"
            f"{reasoning_quality['total_jobs']} "
            f"({reasoning_quality['quality_percentage']:.0f}%)"
        )

    # -----------------------------------------------------
    # Overall calculations
    # -----------------------------------------------------

    if total_students > 0:

        average_category_precision = (
            total_category_precision
            / total_students
        )

        average_role_precision = (
            total_role_precision
            / total_students
        )

    else:

        average_category_precision = 0.0
        average_role_precision = 0.0

    if total_reasoning_evaluated_jobs > 0:

        overall_reasoning_percentage = (
            total_reasoning_quality_passed
            / total_reasoning_evaluated_jobs
        ) * 100

    else:

        overall_reasoning_percentage = 0.0

    # -----------------------------------------------------
    # Overall summary
    # -----------------------------------------------------

    overall_summary = {

        "students_evaluated":
            total_students,

        "category_hit_at_5":
            f"{category_hit_passes}/{total_students}",

        "average_category_precision_at_5":
            round(
                average_category_precision * 100,
                2
            ),

        "top_1_category_relevance":
            f"{category_top1_passes}/{total_students}",

        "role_relevance":
            f"{role_passes}/{total_students}",

        "average_role_precision_at_5":
            round(
                average_role_precision * 100,
                2
            ),

        "skill_consistency":
            f"{skill_consistency_passes}/{total_students}",

        "score_range_valid":
            f"{score_range_passes}/{total_students}",

        "score_ordering_valid":
            f"{score_order_passes}/{total_students}",

        "students_with_all_reasoning_passed":
            f"{students_with_all_reasoning_passed}/{total_students}",

        "overall_reasoning_quality":
            f"{total_reasoning_quality_passed}/"
            f"{total_reasoning_evaluated_jobs}",

        "overall_reasoning_percentage":
            round(
                overall_reasoning_percentage,
                2
            ),

        "total_matched_jobs":
            total_matched_jobs,

        "total_jobs_with_reasoning":
            total_reasoning_jobs
    }

    # -----------------------------------------------------
    # Save complete evaluation results
    # -----------------------------------------------------

    final_results = {

        "evaluation_summary":
            overall_summary,

        "student_results":
            all_results
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_results,
            file,
            indent=4
        )

    # -----------------------------------------------------
    # Final console output
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print(
        "OVERALL MILESTONE 2 EVALUATION"
    )
    print("=" * 60)

    print(
        f"Students evaluated: "
        f"{total_students}"
    )

    print(
        f"Category Hit@5: "
        f"{category_hit_passes}/{total_students}"
    )

    print(
        f"Average Category Precision@5: "
        f"{average_category_precision * 100:.2f}%"
    )

    print(
        f"Top-1 Category Relevance: "
        f"{category_top1_passes}/{total_students}"
    )

    print(
        f"Role relevance: "
        f"{role_passes}/{total_students}"
    )

    print(
        f"Average Role Precision@5: "
        f"{average_role_precision * 100:.2f}%"
    )

    print(
        f"Skill consistency: "
        f"{skill_consistency_passes}/{total_students}"
    )

    print(
        f"Score range valid: "
        f"{score_range_passes}/{total_students}"
    )

    print(
        f"Score ordering valid: "
        f"{score_order_passes}/{total_students}"
    )

    print(
        f"Students with all reasoning passed: "
        f"{students_with_all_reasoning_passed}/"
        f"{total_students}"
    )

    print(
        f"Overall reasoning quality: "
        f"{total_reasoning_quality_passed}/"
        f"{total_reasoning_evaluated_jobs}"
    )

    print(
        f"Overall reasoning percentage: "
        f"{overall_reasoning_percentage:.2f}%"
    )

    print(
        f"Total matched jobs: "
        f"{total_matched_jobs}"
    )

    print()
    print("=" * 60)
    print(
        "EVALUATION COMPLETED"
    )
    print("=" * 60)

    print(
        f"Results saved to:\n"
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()