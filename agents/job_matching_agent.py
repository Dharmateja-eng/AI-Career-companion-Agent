import re


class JobMatchingAgent:

    def __init__(self, model=None):
        self.model = model

    # =========================================================
    # NORMALIZE / EXTRACT SKILLS
    # =========================================================

    def normalize_skills(self, skills):

        if not skills:
            return set()

        if isinstance(skills, list):
            text = " ".join(str(x) for x in skills)
        else:
            text = str(skills)

        text = text.lower()

        known_skills = [
            "spring boot",
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "data science",
            "data analysis",
            "scikit learn",
            "scikit-learn",
            "power bi",
            "cloud computing",
            "rest api",
            "node.js",
            "node js",
            "kubernetes",
            "postgresql",
            "javascript",
            "typescript",
            "tensorflow",
            "pytorch",
            "mongodb",
            "mysql",
            "python",
            "java",
            "flask",
            "django",
            "react",
            "angular",
            "html",
            "css",
            "sql",
            "pandas",
            "numpy",
            "aws",
            "azure",
            "gcp",
            "docker",
            "linux",
            "git",
            "github",
            "devops",
            "selenium",
            "testing",
            "fastapi",
            "tableau",
            "c++",
            "c"
        ]

        found = set()

        for skill in known_skills:

            # -------------------------------------------------
            # C++
            # -------------------------------------------------

            if skill == "c++":

                pattern = r"(?<![a-z0-9])c\+\+(?![a-z0-9])"

                if re.search(pattern, text):
                    found.add("c++")

            # -------------------------------------------------
            # C
            # -------------------------------------------------

            elif skill == "c":

                pattern = r"(?<![a-z0-9])c(?![a-z0-9])"

                if re.search(pattern, text):
                    found.add("c")

            # -------------------------------------------------
            # Normal skills
            # -------------------------------------------------

            else:

                pattern = (
                    r"(?<![a-z0-9])"
                    + re.escape(skill)
                    + r"(?![a-z0-9])"
                )

                if re.search(pattern, text):
                    found.add(skill)

        # Treat scikit-learn and scikit learn as the same skill
        if "scikit-learn" in found:
            found.add("scikit learn")

        # Treat node js and node.js as the same skill
        if "node js" in found:
            found.add("node.js")

        return found

    # =========================================================
    # BUILD COMPLETE JOB TEXT
    # =========================================================

    def build_job_text(self, job):

        if not isinstance(job, dict):
            return ""

        parts = [
            job.get("job_title", ""),
            job.get("title", ""),
            job.get("jobtitle", ""),
            job.get("skills", ""),
            job.get("category", ""),
            job.get("jobdescription", ""),
            job.get("description", ""),
            job.get("experience", ""),
            job.get("education", ""),
            job.get("industry", "")
        ]

        text = " ".join(
            str(part)
            for part in parts
            if part
        )

        return text

    # =========================================================
    # EXTRACT EXPERIENCE YEARS
    # =========================================================

    def extract_years(self, text):

        if not text:
            return 0

        text = str(text).lower()

        matches = re.findall(
            r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)",
            text
        )

        if not matches:
            return 0

        try:
            return max(
                float(x)
                for x in matches
            )
        except Exception:
            return 0

    # =========================================================
    # CALCULATE SKILL SCORE
    # =========================================================

    def calculate_skill_score(
        self,
        candidate_skills,
        job_skills
    ):

        candidate = self.normalize_skills(
            candidate_skills
        )

        required = self.normalize_skills(
            job_skills
        )

        # If no recognizable technical skills
        # are found in the job text, do not penalize.
        if not required:
            return 100, [], []

        matching = candidate.intersection(
            required
        )

        missing = required - candidate

        score = (
            len(matching)
            /
            len(required)
        ) * 100

        return (
            score,
            sorted(matching),
            sorted(missing)
        )

    # =========================================================
    # CALCULATE EDUCATION SCORE
    # =========================================================

    def calculate_education_score(
        self,
        candidate_education,
        job_education
    ):

        # If job does not specify education,
        # consider education satisfied.
        if not job_education:
            return 100

        if not candidate_education:
            return 0

        candidate = str(
            candidate_education
        ).lower()

        required = str(
            job_education
        ).lower()

        keywords = [
            "b.tech",
            "btech",
            "b.e",
            "be",
            "bachelor",
            "m.tech",
            "mtech",
            "master",
            "mba",
            "b.sc",
            "bsc",
            "m.sc",
            "msc",
            "computer science",
            "information technology",
            "engineering",
            "computer applications"
        ]

        candidate_matches = {
            keyword
            for keyword in keywords
            if keyword in candidate
        }

        required_matches = {
            keyword
            for keyword in keywords
            if keyword in required
        }

        # Job education does not contain
        # a recognizable requirement.
        if not required_matches:
            return 100

        # Candidate and job have common
        # education information.
        if candidate_matches.intersection(
            required_matches
        ):
            return 100

        # Some education information exists,
        # but it does not directly match.
        return 50

    # =========================================================
    # CALCULATE EXPERIENCE SCORE
    # =========================================================

    def calculate_experience_score(
        self,
        candidate_experience,
        job_experience
    ):

        required_years = self.extract_years(
            job_experience
        )

        candidate_years = self.extract_years(
            candidate_experience
        )

        # No experience requirement
        if required_years == 0:
            return 100

        # Candidate satisfies requirement
        if candidate_years >= required_years:
            return 100

        # Fresher against experienced role
        if candidate_years == 0:
            return 50

        # Partial experience match
        return min(
            100,
            (
                candidate_years
                /
                required_years
            ) * 100
        )

    # =========================================================
    # CALCULATE FINAL COMPATIBILITY SCORE
    # =========================================================

    def calculate_compatibility_score(
        self,
        candidate,
        job
    ):

        # -----------------------------------------------------
        # Candidate information
        # -----------------------------------------------------

        candidate_skills = candidate.get(
            "skills",
            []
        )

        candidate_education = candidate.get(
            "education",
            ""
        )

        candidate_experience = candidate.get(
            "experience",
            ""
        )

        # -----------------------------------------------------
        # Job information
        # -----------------------------------------------------

        job_education = job.get(
            "education",
            ""
        )

        job_experience = job.get(
            "experience",
            ""
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # The dataset's "skills" column contains broad
        # categories such as:
        #
        # IT Software - Application Programming
        #
        # Therefore we build a complete job text using:
        #
        # job title
        # skills
        # category
        # job description
        # education
        # experience
        # industry
        #
        # This allows technical skills such as Java,
        # Python, SQL, React, AWS, etc. to be detected
        # from the actual job posting.
        # -----------------------------------------------------

        job_text = self.build_job_text(
            job
        )

        # -----------------------------------------------------
        # Skill score
        # -----------------------------------------------------

        (
            skill_score,
            matching_skills,
            missing_skills
        ) = self.calculate_skill_score(
            candidate_skills,
            job_text
        )

        # -----------------------------------------------------
        # Education score
        # -----------------------------------------------------

        education_score = (
            self.calculate_education_score(
                candidate_education,
                job_education
            )
        )

        # -----------------------------------------------------
        # Experience score
        # -----------------------------------------------------

        experience_score = (
            self.calculate_experience_score(
                candidate_experience,
                job_experience
            )
        )

        # -----------------------------------------------------
        # FINAL WEIGHTED SCORE
        #
        # Skills      = 60%
        # Education   = 20%
        # Experience  = 20%
        # -----------------------------------------------------

        final_score = (
            (skill_score * 0.60)
            +
            (education_score * 0.20)
            +
            (experience_score * 0.20)
        )

        # Keep score between 0 and 100
        final_score = max(
            0,
            min(
                100,
                final_score
            )
        )

        return {
            "compatibility_score":
                round(final_score, 2),

            "skill_score":
                round(skill_score, 2),

            "education_score":
                round(education_score, 2),

            "experience_score":
                round(experience_score, 2),

            "matching_skills":
                matching_skills,

            "missing_skills":
                missing_skills
        }

    # =========================================================
    # MATCH CANDIDATE WITH JOBS
    # =========================================================

    def match_jobs(
        self,
        candidate_profile,
        jobs
    ):

        results = []

        # -----------------------------------------------------
        # Make sure jobs is iterable
        # -----------------------------------------------------

        if not jobs:
            return []

        # -----------------------------------------------------
        # Process every retrieved job
        # -----------------------------------------------------

        for job in jobs:

            # Safety check
            if not isinstance(job, dict):
                continue

            score_data = (
                self.calculate_compatibility_score(
                    candidate_profile,
                    job
                )
            )

            matching_skills = (
                score_data[
                    "matching_skills"
                ]
            )

            missing_skills = (
                score_data[
                    "missing_skills"
                ]
            )

            score = (
                score_data[
                    "compatibility_score"
                ]
            )

            # -------------------------------------------------
            # Matching skill explanation
            # -------------------------------------------------

            if matching_skills:

                matching_text = ", ".join(
                    matching_skills[:8]
                )

            else:

                matching_text = (
                    "No major matching skills found"
                )

            # -------------------------------------------------
            # Missing skill explanation
            # -------------------------------------------------

            if missing_skills:

                missing_text = ", ".join(
                    missing_skills[:8]
                )

            else:

                missing_text = (
                    "No major missing skills"
                )

            # -------------------------------------------------
            # Reasoning
            # -------------------------------------------------

            reasoning = (
                f"This job has a compatibility "
                f"score of {score}%. "
                f"Matching skills include "
                f"{matching_text}. "
                f"Skills that may need improvement "
                f"include {missing_text}."
            )

            # -------------------------------------------------
            # Job ID
            # -------------------------------------------------

            job_id = job.get(
                "jobid",
                job.get(
                    "job_id",
                    ""
                )
            )

            # -------------------------------------------------
            # Job title
            # -------------------------------------------------

            job_title = job.get(
                "job_title",
                job.get(
                    "title",
                    job.get(
                        "jobtitle",
                        "Job Opportunity"
                    )
                )
            )

            # -------------------------------------------------
            # Location
            # -------------------------------------------------

            location = job.get(
                "location",
                job.get(
                    "joblocation_address",
                    ""
                )
            )

            # -------------------------------------------------
            # Description
            # -------------------------------------------------

            description = job.get(
                "description",
                job.get(
                    "jobdescription",
                    ""
                )
            )

            # -------------------------------------------------
            # Store result
            # -------------------------------------------------

            results.append({

                "jobid":
                    job_id,

                "job_title":
                    job_title,

                "company":
                    job.get(
                        "company",
                        "Company"
                    ),

                "category":
                    job.get(
                        "category",
                        ""
                    ),

                "description":
                    description,

                "skills":
                    job.get(
                        "skills",
                        ""
                    ),

                "experience":
                    job.get(
                        "experience",
                        ""
                    ),

                "education":
                    job.get(
                        "education",
                        ""
                    ),

                "industry":
                    job.get(
                        "industry",
                        ""
                    ),

                "location":
                    location,

                "payrate":
                    job.get(
                        "payrate",
                        ""
                    ),

                "compatibility_score":
                    score,

                "matching_skills":
                    matching_skills,

                "missing_skills":
                    missing_skills,

                "skill_score":
                    score_data[
                        "skill_score"
                    ],

                "education_score":
                    score_data[
                        "education_score"
                    ],

                "experience_score":
                    score_data[
                        "experience_score"
                    ],

                "reasoning":
                    reasoning
            })

        # =====================================================
        # RANK JOBS BY COMPATIBILITY
        # =====================================================

        results.sort(
            key=lambda x:
                x["compatibility_score"],
            reverse=True
        )

        return results


# =============================================================
# FUNCTION USED BY FLASK APPLICATION
# =============================================================

def match_jobs(
    candidate_profile,
    jobs
):

    agent = JobMatchingAgent()

    results = agent.match_jobs(
        candidate_profile,
        jobs
    )

    return {
        "matched_jobs": results,
        "number_of_jobs": len(results)
    }