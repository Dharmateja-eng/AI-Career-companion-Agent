import os
import json
import ast

from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import (
    db,
    User,
    StudentProfile,
    Resume,
    AIAnalysis,
    Job,
    JobMatch,
    M3SkillGapAnalysis,
    M3ResumeCoverLetter,
    M3InterviewPreparation,
    CareerConversationMessage
)
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from google import genai

from agents.resume_agent import ResumeAgent
from agents.career_agent import CareerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.interview_agent import InterviewAgent
from agents.job_matching_agent import JobMatchingAgent
from agents.m3_skill_gap_agent import M3SkillGapAgent
from agents.m3_resume_cover_letter_agent import M3ResumeCoverLetterAgent
from agents.m3_interview_agent import M3InterviewAgent
from agents.m3_career_assistant_agent import M3CareerAssistantAgent
from agents.m3_mock_interview_agent import M3MockInterviewAgent

# ==========================================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file")


# ==========================================================
# FLASK CONFIGURATION
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

UPLOAD_DIR = r"C:\CareerAI_Uploads"

# Legacy JSON profile cache. Keep it outside OneDrive as well.
LOCAL_DATA_DIR = r"C:\CareerAI_Data"
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
PROFILE_FILE = os.path.join(
    LOCAL_DATA_DIR,
    "candidate_profile.json"
)


# ==========================================================
# CREATE REQUIRED DIRECTORIES
# ==========================================================

os.makedirs(
    DATA_DIR,
    exist_ok=True
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==========================================================
# CREATE FLASK APPLICATION
# ==========================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.config["SECRET_KEY"] = "careerai-development-secret"
# ==========================================================
# SERVER-SIDE SESSION CONFIGURATION
# ==========================================================
app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.config["SECRET_KEY"] = "careerai-development-secret"

SESSION_DIR = r"C:\Users\dharm\careerai_session"
os.makedirs(SESSION_DIR, exist_ok=True)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = SESSION_DIR
app.config["SESSION_PERMANENT"] = False

Session(app)

# Keep the frequently-written SQLite database outside OneDrive.
# This avoids file-lock/synchronization problems during INSERT/COMMIT operations.
DATABASE_DIR = r"C:\CareerAI_Data"
os.makedirs(DATABASE_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATABASE_DIR, "careerai.db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH.replace("\\", "/")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Give SQLite enough time to handle a short-lived file lock.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"timeout": 30}
}

db.init_app(app)


# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

with app.app_context():
    db.create_all()


# ==========================================================
# GEMINI CLIENT
# ==========================================================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ==========================================================
# AI AGENTS - MILESTONE 1
# ==========================================================

resume_agent = ResumeAgent(
    client
)

career_agent = CareerAgent(
    client
)

skill_gap_agent = SkillGapAgent(
    client
)

interview_agent = InterviewAgent(
    client
)


# ==========================================================
# MILESTONE 2 AGENTS
# ==========================================================

job_retrieval_agent = None
job_retrieval_available = False

try:
    from agents.job_retrieval_agent import JobRetrievalAgent
    job_retrieval_agent = JobRetrievalAgent(client)
    job_retrieval_available = True
    print("M2: Job Retrieval Agent loaded successfully.")
except Exception as e:
    print("M2: FAISS/Job Retrieval Agent unavailable.")
    print(f"M2 RETRIEVAL ERROR: {e}")

job_matching_agent = JobMatchingAgent()

# ==========================================================
# MILESTONE 3.1 AGENT
# ==========================================================

m3_skill_gap_agent = M3SkillGapAgent(client)

m3_resume_cover_letter_agent = M3ResumeCoverLetterAgent(client)
m3_interview_agent = M3InterviewAgent(client)
m3_career_assistant_agent = M3CareerAssistantAgent(client)
m3_mock_interview_agent = M3MockInterviewAgent(client)
print("M3 Mock Interview Agent loaded:", m3_mock_interview_agent)
# ==========================================================
# RESUME TEXT EXTRACTION
# ==========================================================

def extract_resume_text(pdf_path):

    text = ""

    reader = PdfReader(
        pdf_path
    )

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            text += page_text + "\n"

    return text.strip()


# ==========================================================
# NORMALIZE JOB MATCHING RESULT
#
# IMPORTANT:
# JobMatchingAgent may return either:
#
# 1. A list
# 2. A dictionary containing "matched_jobs"
#
# This function makes both formats safe.
# ==========================================================

def normalize_job_matching_result(job_matching_result):

    # ------------------------------------------------------
    # CASE 1: JobMatchingAgent returned a LIST
    # ------------------------------------------------------

    if isinstance(
        job_matching_result,
        list
    ):

        return {
            "matched_jobs": job_matching_result,
            "number_of_jobs": len(
                job_matching_result
            )
        }


    # ------------------------------------------------------
    # CASE 2: JobMatchingAgent returned a DICTIONARY
    # ------------------------------------------------------

    if isinstance(
        job_matching_result,
        dict
    ):

        matched_jobs = job_matching_result.get(
            "matched_jobs",
            []
        )

        # Make sure matched_jobs is actually a list
        if not isinstance(
            matched_jobs,
            list
        ):

            matched_jobs = []

        job_matching_result["matched_jobs"] = matched_jobs

        job_matching_result["number_of_jobs"] = len(
            matched_jobs
        )

        return job_matching_result


    # ------------------------------------------------------
    # CASE 3: Unexpected result
    # ------------------------------------------------------

    return {
        "matched_jobs": [],
        "number_of_jobs": 0
    }


# ==========================================================
# DATABASE JOB FALLBACK RETRIEVAL
# ==========================================================

def fallback_retrieve_jobs(candidate_profile, top_k_jobs=5):
    """
    Fallback job retrieval used when FAISS cannot load on the
    current computer. It searches the jobs already stored in
    the SQL database using simple keyword overlap.

    FAISS remains the official Milestone 2 semantic retrieval
    implementation. This fallback only keeps the website usable
    when Windows blocks the FAISS native extension.
    """

    def text_value(value):
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return " ".join(text_value(item) for item in value)
        if isinstance(value, dict):
            return " ".join(text_value(v) for v in value.values())
        return str(value)

    def parse_profile_value(value):
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return text_value(parsed)
            except Exception:
                return value
        return text_value(value)

    def tokenize(text):
        import re
        words = re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
        stop_words = {
            "and", "the", "for", "with", "from", "this", "that",
            "have", "has", "are", "was", "will", "you", "your",
            "student", "candidate", "experience", "education", "skills"
        }
        return {word for word in words if len(word) > 1 and word not in stop_words}

    profile_parts = []

    for key in [
        "name",
        "education",
        "experience",
        "skills",
        "projects",
        "certifications"
    ]:
        profile_parts.append(parse_profile_value(candidate_profile.get(key, "")))

    candidate_text = " ".join(profile_parts)
    candidate_tokens = tokenize(candidate_text)

    if not candidate_tokens:
        return []

    jobs = Job.query.all()
    scored_jobs = []

    for job in jobs:
        job_text = " ".join([
            text_value(job.title),
            text_value(job.company),
            text_value(job.category),
            text_value(job.description),
            text_value(job.skills),
            text_value(job.experience),
            text_value(job.education),
            text_value(job.industry),
            text_value(job.location)
        ])

        job_tokens = tokenize(job_text)
        if not job_tokens:
            continue

        overlap = candidate_tokens.intersection(job_tokens)
        score = len(overlap)

        # Give extra weight to direct skill/title/category matches.
        skill_tokens = tokenize(text_value(job.skills))
        title_tokens = tokenize(
            text_value(job.title) + " " + text_value(job.category)
        )

        score += 2 * len(candidate_tokens.intersection(skill_tokens))
        score += 3 * len(candidate_tokens.intersection(title_tokens))

        scored_jobs.append((score, job, overlap))

    scored_jobs.sort(key=lambda item: item[0], reverse=True)

    selected = scored_jobs[:top_k_jobs]

    # If keyword overlap is weak, still provide a small set of jobs
    # so the Job Matching Agent can perform the detailed comparison.
    if len(selected) < top_k_jobs:
        selected_ids = {job.id for _, job, _ in selected}
        for job in jobs:
            if job.id not in selected_ids:
                selected.append((0, job, set()))
            if len(selected) >= top_k_jobs:
                break

    retrieved_jobs = []

    for rank, (score, job, overlap) in enumerate(selected[:top_k_jobs], start=1):
        retrieved_jobs.append({
            "jobid": job.job_id or str(job.id),
            "job_title": job.title or "Job Opportunity",
            "company": job.company or "Company",
            "category": job.category or "",
            "skills": job.skills or "",
            "experience": job.experience or "",
            "education": job.education or "",
            "location": job.location or "",
            "payrate": job.payrate or "",
            "industry": job.industry or "",
            "jobdescription": job.description or "",
            "retrieval_score": round(float(score), 4),
            "retrieval_rank": rank
        })

    print(
        f"M2 FALLBACK: Retrieved {len(retrieved_jobs)} jobs from SQL database."
    )

    return retrieved_jobs


# ==========================================================
# SAVE RESUME + AI RESULTS TO DATABASE
# ==========================================================

def save_analysis_to_database(
    user_id,
    filename,
    resume_text,
    candidate_profile,
    resume_analysis,
    career_result,
    skill_gap_result,
    interview_result,
    retrieved_jobs,
    job_matching_result
):

    # ------------------------------------------------------
    # FINAL SAFETY CHECK FOR JOB MATCHING RESULT
    # ------------------------------------------------------

    job_matching_result = normalize_job_matching_result(
        job_matching_result
    )

    matched_jobs = job_matching_result[
        "matched_jobs"
    ]


    # ------------------------------------------------------
    # 1. SAVE RESUME
    # ------------------------------------------------------

    resume_record = Resume(
        user_id=user_id,
        filename=filename,
        resume_text=resume_text
    )

    db.session.add(
        resume_record
    )


    # ------------------------------------------------------
    # 2. SAVE / UPDATE STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()


    if student_profile is None:

        student_profile = StudentProfile(
            user_id=user_id
        )

        db.session.add(
            student_profile
        )


    student_profile.education = json.dumps(
        candidate_profile.get(
            "education",
            []
        ),
        ensure_ascii=False
    )


    student_profile.experience = json.dumps(
        candidate_profile.get(
            "experience",
            []
        ),
        ensure_ascii=False
    )


    student_profile.skills = json.dumps(
        candidate_profile.get(
            "skills",
            []
        ),
        ensure_ascii=False
    )


    student_profile.projects = json.dumps(
        candidate_profile.get(
            "projects",
            []
        ),
        ensure_ascii=False
    )


    student_profile.certifications = json.dumps(
        candidate_profile.get(
            "certifications",
            []
        ),
        ensure_ascii=False
    )


    # ------------------------------------------------------
    # 3. SAVE MILESTONE 1 AI ANALYSIS
    # ------------------------------------------------------

    ai_analysis = AIAnalysis(

        user_id=user_id,

        resume_analysis=json.dumps(
            resume_analysis,
            ensure_ascii=False
        ),

        career_recommendations=json.dumps(
            career_result,
            ensure_ascii=False
        ),

        skill_gap=json.dumps(
            skill_gap_result,
            ensure_ascii=False
        ),

        interview_preparation=json.dumps(
            interview_result,
            ensure_ascii=False
        )
    )

    db.session.add(
        ai_analysis
    )


    # ------------------------------------------------------
    # 4. REMOVE PREVIOUS JOB MATCHES
    # ------------------------------------------------------

    JobMatch.query.filter_by(
        user_id=user_id
    ).delete()


    # ------------------------------------------------------
    # 5. SAVE MILESTONE 2 JOB MATCHES
    # ------------------------------------------------------

    for job in matched_jobs:

        # Safety check
        if not isinstance(
            job,
            dict
        ):
            continue


        job_id = (
            job.get("jobid")
            or job.get("job_id")
            or job.get("id")
            or ""
        )


        # Skip jobs without an ID
        if not job_id:
            continue


        compatibility_score = job.get(
            "compatibility_score",
            0
        )


        # Make sure compatibility score is numeric
        try:

            compatibility_score = float(
                compatibility_score
            )

        except (
            TypeError,
            ValueError
        ):

            compatibility_score = 0.0


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


        match_record = JobMatch(

            user_id=user_id,

            job_id=str(
                job_id
            ),

            compatibility_score=compatibility_score,

            matching_skills=json.dumps(
                matching_skills,
                ensure_ascii=False
            ),

            missing_skills=json.dumps(
                missing_skills,
                ensure_ascii=False
            ),

            reasoning=str(
                reasoning
            )
        )


        db.session.add(
            match_record
        )


    # ------------------------------------------------------
    # 6. COMMIT EVERYTHING
    # ------------------------------------------------------

    db.session.commit()


    print(
        "DATABASE: Resume saved"
    )

    print(
        "DATABASE: Student profile saved"
    )

    print(
        "DATABASE: M1 analysis saved"
    )

    print(
        f"DATABASE: {len(matched_jobs)} M2 job matches saved"
    )


# ==========================================================
# EMPTY DASHBOARD PROFILE
# ==========================================================

def get_empty_profile():

    return {

        "student_profile": {

            "name": session.get(
                "user_name",
                ""
            ),

            "email": session.get(
                "user_email",
                ""
            ),

            "phone": "",

            "education": [],

            "experience": [],

            "skills": [],

            "projects": [],

            "certifications": []

        },


        "resume": {

            "filename": "",

            "extracted_text": "",

            "llm_extracted_profile": {

                "name": session.get(
                    "user_name",
                    ""
                ),

                "email": session.get(
                    "user_email",
                    ""
                ),

                "phone": "",

                "skills": [],

                "education": [],

                "experience": [],

                "projects": [],

                "certifications": []

            }

        },


        "resume_analysis": {

            "resume_score": 0,

            "strengths": [],

            "weaknesses": [],

            "improvements": []

        },


        "career_analysis": {

            "recommended_roles": []

        },


        "skill_gap_analysis": {

            "target_role": "",

            "current_skills": [],

            "required_skills": [],

            "matching_skills": [],

            "missing_skills": [],

            "skills_to_improve": [],

            "recommendations": []

        },


        "job_retrieval_analysis": {

            "retrieved_jobs": [],

            "number_of_jobs": 0

        },


        "job_matching_analysis": {

            "matched_jobs": []

        },


        "interview_analysis": {

            "target_role": "",

            "technical_questions": [],

            "conceptual_questions": [],

            "hr_questions": [],

            "preparation_tips": []

        }

    }


# ==========================================================
# SIGNUP
# ==========================================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)

def signup():

    if request.method == "GET":

        return render_template(
            "signup.html"
        )


    print(
        "SIGNUP POST REQUEST RECEIVED"
    )


    name = request.form.get(
        "name",
        ""
    ).strip()


    email = request.form.get(
        "email",
        ""
    ).strip().lower()


    password = request.form.get(
        "password",
        ""
    )


    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    if password != confirm_password:

        return render_template(
            "signup.html",
            error="Passwords do not match."
        )


    if len(password) < 6:

        return render_template(
            "signup.html",
            error="Password must be at least 6 characters."
        )


    existing_user = User.query.filter_by(
        email=email
    ).first()


    if existing_user:

        return render_template(
            "signup.html",
            error="An account with this email already exists."
        )


    password_hash = generate_password_hash(
        password
    )


    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash
    )


    db.session.add(
        new_user
    )


    db.session.commit()


    return redirect(
        url_for("login")
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)

def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )


    email = request.form.get(
        "email",
        ""
    ).strip().lower()


    password = request.form.get(
        "password",
        ""
    )


    user = User.query.filter_by(
        email=email
    ).first()


    if (
        user is None
        or not check_password_hash(
            user.password_hash,
            password
        )
    ):

        return render_template(
            "login.html",
            error="Invalid email or password."
        )


    session["user_id"] = user.id

    session["user_email"] = user.email

    session["user_name"] = user.name


    return redirect(
        url_for("resume_upload")
    )


# ==========================================================
# RESUME UPLOAD PAGE
# ==========================================================

@app.route(
    "/resume-upload",
    methods=["GET"]
)

def resume_upload():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    return render_template(
        "profile.html"
    )


# ==========================================================
# HOME / RESUME PROCESSING
# ==========================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)

def profile():

    if request.method == "GET":

        return render_template(
            "login.html"
        )


    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    resume = request.files.get(
        "resume"
    )


    if not resume or resume.filename == "":

        return "Please upload a resume PDF."


    if not resume.filename.lower().endswith(
        ".pdf"
    ):

        return "Please upload a PDF resume."


    filename = secure_filename(
        resume.filename
    )


    if not filename:

        return "Invalid resume filename."


    # ======================================================
    # SAVE USER-SPECIFIC RESUME
    # ======================================================

    user_upload_dir = os.path.join(
        UPLOAD_DIR,
        str(
            session["user_id"]
        )
    )


    os.makedirs(
        user_upload_dir,
        exist_ok=True
    )


    resume_path = os.path.join(
        user_upload_dir,
        filename
    )


    resume.save(
        resume_path
    )


    print(
        f"RESUME SAVED: {resume_path}"
    )


    # ======================================================
    # EXTRACT RESUME TEXT
    # ======================================================

    try:

        resume_text = extract_resume_text(
            resume_path
        )

    except Exception as e:

        return (
            f"Error reading resume: {str(e)}"
        )


    if not resume_text:

        return (
            "Could not extract text from the resume."
        )


    # ======================================================
    # RESUME AGENT
    # ======================================================

    try:

        resume_result = resume_agent.analyze(
            resume_text
        )

    except Exception as e:

        return (
            f"Resume Agent Error: {str(e)}"
        )


    candidate_profile = resume_result.get(
        "candidate_profile",
        {}
    )


    resume_analysis = resume_result.get(
        "resume_analysis",
        {}
    )


    # ======================================================
    # JOB RETRIEVAL AGENT
    # ======================================================

    retrieved_jobs = []

    job_retrieval_error = ""


    if job_retrieval_available and job_retrieval_agent is not None:

        try:
            retrieved_jobs = job_retrieval_agent.retrieve_jobs(
                candidate_profile,
                top_k_chunks=15,
                top_k_jobs=5
            )
            print(f"M2: Retrieved {len(retrieved_jobs)} jobs.")

        except Exception as e:
            job_retrieval_error = str(e)
            retrieved_jobs = []
            print(f"M2 RETRIEVAL ERROR: {e}")

    else:
        job_retrieval_error = "FAISS retrieval is unavailable on this computer."
        print("M2: FAISS retrieval skipped.")

        # --------------------------------------------------
        # WEBSITE FALLBACK
        # --------------------------------------------------
        # FAISS is blocked by the Windows Application Control
        # policy on this computer. Use the 200 jobs already
        # stored in the SQL database so the website can still
        # generate personalized job matches.
        try:
            retrieved_jobs = fallback_retrieve_jobs(
                candidate_profile,
                top_k_jobs=5
            )

            if retrieved_jobs:
                print(
                    f"M2 FALLBACK: {len(retrieved_jobs)} jobs ready for matching."
                )
                job_retrieval_error = ""
            else:
                print("M2 FALLBACK: No usable jobs found in SQL database.")

        except Exception as e:
            job_retrieval_error = str(e)
            retrieved_jobs = []
            print(f"M2 FALLBACK ERROR: {e}")


    # ======================================================
    # JOB MATCHING AGENT
    # ======================================================

    # Default safe structure
    job_matching_result = {

        "matched_jobs": [],

        "number_of_jobs": 0

    }


    if retrieved_jobs:

        try:

            job_matching_result = (
                job_matching_agent.match_jobs(
                    candidate_profile,
                    retrieved_jobs
                )
            )


            # ==================================================
            # IMPORTANT FIX
            # ==================================================
            # Convert LIST result into the expected dictionary.
            #
            # This prevents:
            #
            # 'list' object has no attribute 'get'
            # ==================================================

            job_matching_result = (
                normalize_job_matching_result(
                    job_matching_result
                )
            )


            print(
                "JOB MATCHING RESULT TYPE:",
                type(
                    job_matching_result
                ).__name__
            )


            print(
                "NUMBER OF MATCHED JOBS:",
                len(
                    job_matching_result[
                        "matched_jobs"
                    ]
                )
            )


        except Exception as e:

            print(
                f"JOB MATCHING ERROR: {e}"
            )


            job_matching_result = {

                "matched_jobs": [],

                "number_of_jobs": 0,

                "error": str(e)

            }


    elif job_retrieval_error:

        job_matching_result = {

            "matched_jobs": [],

            "number_of_jobs": 0,

            "error": job_retrieval_error

        }


    # ======================================================
    # CAREER AGENT
    # ======================================================

    try:

        career_result = career_agent.recommend(
            candidate_profile
        )

    except Exception as e:

        return (
            f"Career Agent Error: {str(e)}"
        )


    recommended_roles = career_result.get(
        "recommended_roles",
        []
    )


    target_role = ""


    if recommended_roles:

        target_role = recommended_roles[0].get(
            "role",
            ""
        )


    # ======================================================
    # SKILL GAP AGENT
    # ======================================================

    skill_gap_result = {}


    if target_role:

        try:

            skill_gap_result = (
                skill_gap_agent.analyze(
                    candidate_profile,
                    target_role
                )
            )

        except Exception as e:

            skill_gap_result = {

                "target_role": target_role,

                "current_skills": [],

                "required_skills": [],

                "matching_skills": [],

                "missing_skills": [],

                "skills_to_improve": [],

                "recommendations": [],

                "error": str(e)

            }


    # ======================================================
    # INTERVIEW AGENT
    # ======================================================

    interview_result = {}


    if target_role:

        try:

            interview_result = (
                interview_agent.generate_interview(
                    candidate_profile,
                    target_role,
                    skill_gap_result
                )
            )

        except Exception as e:

            interview_result = {

                "target_role": target_role,

                "technical_questions": [],

                "conceptual_questions": [],

                "hr_questions": [],

                "preparation_tips": [],

                "error": str(e)

            }


    # ======================================================
    # COMPLETE CANDIDATE PROFILE
    # ======================================================

    profile_data = {

        "student_profile": {

            "name": candidate_profile.get(
                "name",
                ""
            ),

            "email": candidate_profile.get(
                "email",
                ""
            ),

            "phone": candidate_profile.get(
                "phone",
                ""
            )

        },


        "resume": {

            "filename": filename,

            "extracted_text": resume_text,

            "llm_extracted_profile": candidate_profile

        },


        "resume_analysis": resume_analysis,


        "career_analysis": {

            "recommended_roles": recommended_roles

        },


        "skill_gap_analysis": skill_gap_result,


        "interview_analysis": interview_result,


        "job_retrieval_analysis": {

            "retrieved_jobs": retrieved_jobs,

            "number_of_jobs": len(
                retrieved_jobs
            )

        },


        "job_matching_analysis": job_matching_result

    }


    # ======================================================
    # SAVE CANDIDATE PROFILE
    # ======================================================

    try:

        with open(
            PROFILE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                profile_data,
                file,
                indent=4,
                ensure_ascii=False
            )

    except Exception as e:

        print(
            f"PROFILE JSON SAVE WARNING: {e}"
        )

        print(
            "Continuing because the profile is also stored in the database."
        )


    # ======================================================
    # SAVE DATABASE
    # ======================================================

    try:

        save_analysis_to_database(

            user_id=session["user_id"],

            filename=filename,

            resume_text=resume_text,

            candidate_profile=candidate_profile,

            resume_analysis=resume_analysis,

            career_result=career_result,

            skill_gap_result=skill_gap_result,

            interview_result=interview_result,

            retrieved_jobs=retrieved_jobs,

            job_matching_result=job_matching_result

        )

    except Exception as e:

        db.session.rollback()

        print(
            f"DATABASE ERROR: {e}"
        )

        return (
            f"Error saving analysis to database: {str(e)}"
        )


    # ======================================================
    # AFTER RESUME PROCESSING → DATABASE DASHBOARD
    # ======================================================

    return redirect(
        url_for("dashboard")
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@app.route(
    "/dashboard"
)

def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user_id = session["user_id"]


    user = User.query.get(
        user_id
    )


    resume_record = (
        Resume.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            Resume.uploaded_at.desc()
        )
        .first()
    )


    student_profile = (
        StudentProfile.query
        .filter_by(
            user_id=user_id
        )
        .first()
    )


    ai_analysis = (
        AIAnalysis.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
        .first()
    )


    job_matches = (
        JobMatch.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            JobMatch.compatibility_score.desc()
        )
        .all()
    )


    profile_data = get_empty_profile()


    if user:

        profile_data["student_profile"]["name"] = user.name

        profile_data["student_profile"]["email"] = user.email

        profile_data["resume"]["llm_extracted_profile"]["name"] = user.name

        profile_data["resume"]["llm_extracted_profile"]["email"] = user.email


    if resume_record:

        profile_data["resume"]["filename"] = (
            resume_record.filename or ""
        )

        profile_data["resume"]["extracted_text"] = (
            resume_record.resume_text or ""
        )


    if student_profile:

        try:

            profile_data["student_profile"]["education"] = (
                json.loads(
                    student_profile.education
                )
                if student_profile.education
                else []
            )


            profile_data["student_profile"]["experience"] = (
                json.loads(
                    student_profile.experience
                )
                if student_profile.experience
                else []
            )


            profile_data["student_profile"]["skills"] = (
                json.loads(
                    student_profile.skills
                )
                if student_profile.skills
                else []
            )


            profile_data["student_profile"]["projects"] = (
                json.loads(
                    student_profile.projects
                )
                if student_profile.projects
                else []
            )


            profile_data["student_profile"]["certifications"] = (
                json.loads(
                    student_profile.certifications
                )
                if student_profile.certifications
                else []
            )


            profile_data["resume"]["llm_extracted_profile"]["skills"] = (
                json.loads(
                    student_profile.skills
                )
                if student_profile.skills
                else []
            )


            profile_data["resume"]["llm_extracted_profile"]["education"] = (
                json.loads(
                    student_profile.education
                )
                if student_profile.education
                else []
            )


            profile_data["resume"]["llm_extracted_profile"]["experience"] = (
                json.loads(
                    student_profile.experience
                )
                if student_profile.experience
                else []
            )


            profile_data["resume"]["llm_extracted_profile"]["projects"] = (
                json.loads(
                    student_profile.projects
                )
                if student_profile.projects
                else []
            )


            profile_data["resume"]["llm_extracted_profile"]["certifications"] = (
                json.loads(
                    student_profile.certifications
                )
                if student_profile.certifications
                else []
            )


        except Exception as e:

            print(
                f"DATABASE PROFILE READ ERROR: {e}"
            )


    if ai_analysis:

        try:

            profile_data["resume_analysis"] = (
                json.loads(
                    ai_analysis.resume_analysis
                )
                if ai_analysis.resume_analysis
                else {}
            )


            career_data = (
                json.loads(
                    ai_analysis.career_recommendations
                )
                if ai_analysis.career_recommendations
                else {}
            )


            if isinstance(
                career_data,
                dict
            ):

                profile_data["career_analysis"] = career_data

            else:

                profile_data["career_analysis"] = {

                    "recommended_roles": career_data

                }


            profile_data["skill_gap_analysis"] = (
                json.loads(
                    ai_analysis.skill_gap
                )
                if ai_analysis.skill_gap
                else {}
            )


            profile_data["interview_analysis"] = (
                json.loads(
                    ai_analysis.interview_preparation
                )
                if ai_analysis.interview_preparation
                else {}
            )


        except Exception as e:

            print(
                f"DATABASE AI ANALYSIS READ ERROR: {e}"
            )


    # ======================================================
    # BUILD MATCHED JOB LIST
    # ======================================================

    matched_jobs = []


    for match in job_matches:

        job = Job.query.filter_by(
            job_id=match.job_id
        ).first()


        if job is None:

            continue


        try:

            matching_skills = (
                json.loads(
                    match.matching_skills
                )
                if match.matching_skills
                else []
            )

        except Exception:

            matching_skills = []


        try:

            missing_skills = (
                json.loads(
                    match.missing_skills
                )
                if match.missing_skills
                else []
            )

        except Exception:

            missing_skills = []


        matched_jobs.append({

            "jobid": job.job_id,

            "job_title": job.title or "Job Opportunity",

            "title": job.title or "Job Opportunity",

            "company": job.company or "Company",

            "category": job.category or "",

            "description": job.description or "",

            "skills": job.skills or "",

            "experience": job.experience or "",

            "education": job.education or "",

            "industry": job.industry or "",

            "location": job.location or "",

            "payrate": job.payrate or "",


            # ==================================================
            # JOB MATCHING PERCENTAGE
            # ==================================================

            "compatibility_score": round(
                float(
                    match.compatibility_score or 0
                ),
                2
            ),


            "matching_skills": matching_skills,

            "missing_skills": missing_skills,

            "reasoning": match.reasoning or ""

        })


    profile_data["job_retrieval_analysis"] = {

        "retrieved_jobs": matched_jobs,

        "number_of_jobs": len(
            matched_jobs
        )

    }


    profile_data["job_matching_analysis"] = {

        "matched_jobs": matched_jobs

    }


    return render_template(

        "dashboard.html",

        profile=profile_data

    )


# ==========================================================
# PROFILE PAGE
# ==========================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)

def profile_page():

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user_id = session["user_id"]


    # ------------------------------------------------------
    # GET USER
    # ------------------------------------------------------

    user = User.query.get(
        user_id
    )


    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )


    # ------------------------------------------------------
    # GET OR CREATE STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()


    if student_profile is None:

        student_profile = StudentProfile(
            user_id=user_id,
            education=json.dumps([]),
            experience=json.dumps([]),
            skills=json.dumps([]),
            projects=json.dumps([]),
            certifications=json.dumps([])
        )

        db.session.add(
            student_profile
        )

        db.session.commit()


    # ======================================================
    # SAVE PROFILE
    # ======================================================

    if request.method == "POST":

        education = request.form.get(
            "education",
            ""
        ).strip()


        experience = request.form.get(
            "experience",
            ""
        ).strip()


        skills = request.form.get(
            "skills",
            ""
        ).strip()


        projects = request.form.get(
            "projects",
            ""
        ).strip()


        certifications = request.form.get(
            "certifications",
            ""
        ).strip()


        # --------------------------------------------------
        # Store each field as a simple list
        # --------------------------------------------------

        student_profile.education = json.dumps(
            [education] if education else [],
            ensure_ascii=False
        )


        student_profile.experience = json.dumps(
            [experience] if experience else [],
            ensure_ascii=False
        )


        student_profile.skills = json.dumps(
            [
                skill.strip()
                for skill in skills.split(",")
                if skill.strip()
            ],
            ensure_ascii=False
        )


        student_profile.projects = json.dumps(
            [projects] if projects else [],
            ensure_ascii=False
        )


        student_profile.certifications = json.dumps(
            [
                certification.strip()
                for certification in certifications.split(",")
                if certification.strip()
            ],
            ensure_ascii=False
        )


        db.session.commit()


        return redirect(
            url_for("profile_page")
        )


    # ======================================================
    # PREPARE DATA FOR DISPLAY
    # ======================================================

    def load_json_list(value):

        if not value:

            return []


        try:

            data = json.loads(value)


            if isinstance(data, list):

                return data


            return [data]


        except Exception:

            return []


    education = load_json_list(
        student_profile.education
    )


    experience = load_json_list(
        student_profile.experience
    )


    skills = load_json_list(
        student_profile.skills
    )


    projects = load_json_list(
        student_profile.projects
    )


    certifications = load_json_list(
        student_profile.certifications
    )


    # ------------------------------------------------------
    # SEND DATA TO PROFILE PAGE
    # ------------------------------------------------------

    return render_template(

        "profile_page.html",

        user=user,

        student_profile=student_profile,

        education=education,

        experience=experience,

        skills=skills,

        projects=projects,

        certifications=certifications

    )


# ==========================================================
# RESUME PAGE
# ==========================================================

@app.route("/resume")
def resume_page():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user_id = session["user_id"]


    user = User.query.get(user_id)


    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )


    # Get the user's latest resume
    resume = (
        Resume.query
        .filter_by(user_id=user_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )


    # Get the user's latest AI analysis
    analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )


    # Default values
    resume_analysis = {}


    if analysis and analysis.resume_analysis:

        try:

            resume_analysis = json.loads(
                analysis.resume_analysis
            )

        except Exception:

            resume_analysis = {}


    return render_template(
        "resume_page.html",
        user=user,
        resume=resume,
        analysis=analysis,
        resume_analysis=resume_analysis
    )


# ==========================================================
# CAREER PAGE
# ==========================================================

@app.route("/career")
def career_page():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # Get latest career analysis from database
    analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )

    career_analysis = {
        "recommended_roles": [],
        "career_paths": [],
        "recommendations": []
    }

    if analysis and analysis.career_recommendations:

        try:

            data = json.loads(
                analysis.career_recommendations
            )

            if isinstance(data, dict):

                career_analysis.update(data)

                # Fix recommended roles if they are stored
                # as dictionary strings
                roles = career_analysis.get(
                    "recommended_roles",
                    []
                )

                fixed_roles = []

                if isinstance(roles, list):

                    for role in roles:

                        if isinstance(role, dict):

                            fixed_roles.append(role)

                        elif isinstance(role, str):

                            try:
                                # First try JSON
                                fixed_role = json.loads(role)

                                if isinstance(fixed_role, dict):
                                    fixed_roles.append(fixed_role)

                            except Exception:

                                try:
                                    # Handle Python dictionary format
                                    fixed_role = ast.literal_eval(role)

                                    if isinstance(fixed_role, dict):
                                        fixed_roles.append(fixed_role)

                                except Exception:
                                    pass

                career_analysis["recommended_roles"] = fixed_roles

        except Exception as e:

            print("Career analysis error:", e)

    return render_template(
        "career_page.html",
        user=user,
        career_analysis=career_analysis
    )

# ==========================================================
# OPPORTUNITIES PAGE
# ==========================================================

@app.route(
    "/opportunities"
)

def opportunities_page():

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user_id = session["user_id"]


    # ------------------------------------------------------
    # GET USER JOB MATCHES
    # ------------------------------------------------------

    job_matches = (
        JobMatch.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            JobMatch.compatibility_score.desc()
        )
        .all()
    )


    opportunities = []


    # ------------------------------------------------------
    # GET ACTUAL JOB DETAILS
    # ------------------------------------------------------

    for match in job_matches:

        job = Job.query.filter_by(
            job_id=match.job_id
        ).first()


        if job is None:

            continue


        # --------------------------------------------------
        # MATCHING SKILLS
        # --------------------------------------------------

        try:

            matching_skills = (
                json.loads(
                    match.matching_skills
                )
                if match.matching_skills
                else []
            )

        except Exception:

            matching_skills = []


        # --------------------------------------------------
        # MISSING SKILLS
        # --------------------------------------------------

        try:

            missing_skills = (
                json.loads(
                    match.missing_skills
                )
                if match.missing_skills
                else []
            )

        except Exception:

            missing_skills = []


        # --------------------------------------------------
        # COMPATIBILITY / JOB MATCHING PERCENTAGE
        # --------------------------------------------------

        compatibility_score = round(
            float(
                match.compatibility_score or 0
            ),
            2
        )


        # --------------------------------------------------
        # ADD JOB
        # --------------------------------------------------

        opportunities.append({

            "jobid": job.job_id,

            "title": job.title or "Job Opportunity",

            "company": job.company or "Company",

            "category": job.category or "",

            "description": job.description or "",

            "skills": job.skills or "",

            "experience": job.experience or "",

            "education": job.education or "",

            "industry": job.industry or "",

            "location": job.location or "",

            "payrate": job.payrate or "",


            # ==================================================
            # COMPATIBILITY PERCENTAGE
            # ==================================================

            "compatibility_score": compatibility_score,


            "matching_skills": matching_skills,

            "missing_skills": missing_skills,

            "reasoning": match.reasoning or "",

            "skill_gap_url": url_for(
                "analyze_skill_gap",
                job_id=job.job_id
            )

        })


    # ------------------------------------------------------
    # DISPLAY OPPORTUNITIES
    # ------------------------------------------------------

    return render_template(

        "opportunities_page.html",

        opportunities=opportunities,

        matched_jobs=opportunities,

        number_of_jobs=len(
            opportunities
        )

    )


# ==========================================================
# MILESTONE 3.1 - SELECTED JOB SKILL GAP ANALYSIS
# ==========================================================
@app.route("/analyze-skill-gap/<job_id>", methods=["GET", "POST"])
def analyze_skill_gap(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    job = Job.query.filter_by(job_id=str(job_id)).first()
    if job is None:
        return "Selected job was not found.", 404

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return "Student profile not found. Please upload your resume first."

    def load_json_field(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except Exception:
            return value

    candidate_profile = {
        "name": user.name or "",
        "email": user.email or "",
        "education": load_json_field(student_profile.education),
        "experience": load_json_field(student_profile.experience),
        "skills": load_json_field(student_profile.skills),
        "projects": load_json_field(student_profile.projects),
        "certifications": load_json_field(student_profile.certifications)
    }

    selected_job = {
        "job_id": job.job_id,
        "job_title": job.title or "",
        "company": job.company or "",
        "category": job.category or "",
        "description": job.description or "",
        "skills": job.skills or "",
        "experience": job.experience or "",
        "education": job.education or "",
        "industry": job.industry or "",
        "location": job.location or "",
        "payrate": job.payrate or ""
    }

    try:
        result = m3_skill_gap_agent.analyze(candidate_profile, selected_job)
    except Exception as e:
        db.session.rollback()
        print(f"M3.1 SKILL GAP ERROR: {e}")
        return f"M3.1 Skill Gap Agent Error: {str(e)}", 500

    if not isinstance(result, dict):
        result = {
            "job_id": job.job_id,
            "job_title": job.title or "",
            "critical_missing_skills": [],
            "partially_demonstrated_skills": [],
            "preferred_skills": [],
            "experience_gaps": [],
            "qualification_gaps": [],
            "gap_explanations": [],
            "recommendations": [],
            "error": "Unexpected response from M3 Skill Gap Agent."
        }

    try:
        analysis_record = M3SkillGapAnalysis(
            user_id=user_id,
            job_id=str(job.job_id),
            analysis=json.dumps(result, ensure_ascii=False)
        )
        db.session.add(analysis_record)
        db.session.commit()
        print(f"M3.1: Skill gap analysis saved for job {job.job_id}.")
    except Exception as e:
        db.session.rollback()
        print(f"M3.1 DATABASE ERROR: {e}")
        return f"Error saving M3.1 skill gap analysis: {str(e)}", 500

    return redirect(url_for("skill_gap_page", job_id=job.job_id))


# ==========================================================
# MILESTONE 3.2 - RESUME + COVER LETTER CUSTOMIZATION
# ==========================================================

@app.route(
    "/customize-application/<job_id>",
    methods=["GET", "POST"]
)
def customize_application(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # GET SELECTED JOB
    # ------------------------------------------------------

    job = Job.query.filter_by(
        job_id=str(job_id)
    ).first()

    if job is None:
        return "Selected job was not found.", 404

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return (
            "Student profile not found. "
            "Please upload your resume first."
        ), 404

    # ------------------------------------------------------
    # LOAD PROFILE JSON FIELDS
    # ------------------------------------------------------

    def load_json_field(value):
        if not value:
            return []

        try:
            return json.loads(value)
        except Exception:
            return value

    candidate_profile = {
        "name": user.name or "",
        "email": user.email or "",
        "education": load_json_field(
            student_profile.education
        ),
        "experience": load_json_field(
            student_profile.experience
        ),
        "skills": load_json_field(
            student_profile.skills
        ),
        "projects": load_json_field(
            student_profile.projects
        ),
        "certifications": load_json_field(
            student_profile.certifications
        )
    }

    # ------------------------------------------------------
    # PREPARE SELECTED JOB
    # ------------------------------------------------------

    selected_job = {
        "job_id": job.job_id,
        "jobtitle": job.title or "",
        "job_title": job.title or "",
        "company": job.company or "",
        "jobdescription": job.description or "",
        "description": job.description or "",
        "skills": job.skills or "",
        "experience": job.experience or "",
        "education": job.education or "",
        "industry": job.industry or "",
        "location": job.location or "",
        "payrate": job.payrate or ""
    }

    # ------------------------------------------------------
    # RUN M3.2 AGENT
    # ------------------------------------------------------

    try:

        result = m3_resume_cover_letter_agent.customize(
            candidate_profile,
            selected_job
        )

    except Exception as e:

        db.session.rollback()

        print(
            f"M3.2 CUSTOMIZATION ERROR: {e}"
        )

        return (
            f"M3.2 Resume/Cover Letter Agent Error: {str(e)}",
            500
        )

    # ------------------------------------------------------
    # SAFETY CHECK
    # ------------------------------------------------------

    if not isinstance(result, dict):

        result = {
            "job_id": job.job_id,
            "job_title": job.title or "",
            "relevant_skills": [],
            "relevant_projects": [],
            "relevant_experience": [],
            "relevant_certifications": [],
            "priority_sections": [],
            "improved_bullet_points": [],
            "recommended_keywords": [],
            "tailored_resume_summary": "",
            "cover_letter": "",
            "review_notes": [],
            "error": (
                "Unexpected response from "
                "M3 Resume and Cover Letter Agent."
            )
        }

    # ------------------------------------------------------
    # SAVE M3.2 RESULT TO DATABASE
    # ------------------------------------------------------

    try:

        application_record = M3ResumeCoverLetter(
            user_id=user_id,
            job_id=str(job.job_id),
            tailored_resume=json.dumps(
                result,
                ensure_ascii=False
            ),
            cover_letter=str(
                result.get(
                    "cover_letter",
                    ""
                )
            )
        )

        db.session.add(
            application_record
        )

        db.session.commit()

        print(
            f"M3.2: Resume and cover letter saved "
            f"for job {job.job_id}."
        )

    except Exception as e:

        db.session.rollback()

        print(
            f"M3.2 DATABASE ERROR: {e}"
        )

        return (
            f"Error saving M3.2 application: {str(e)}",
            500
        )

    # ------------------------------------------------------
    # DISPLAY M3.2 RESULT
    # ------------------------------------------------------

    return render_template(
        "resume_customization_page.html",
        user=user,
        result=result,
        selected_job=selected_job
    )



# ==========================================================
# MILESTONE 3.3 - INTERVIEW PREPARATION
# ==========================================================

@app.route(
    "/prepare-interview/<job_id>",
    methods=["GET", "POST"]
)
def prepare_interview(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # GET SELECTED JOB
    # ------------------------------------------------------

    job = Job.query.filter_by(
        job_id=str(job_id)
    ).first()

    if job is None:
        return "Selected job was not found.", 404

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return (
            "Student profile not found. "
            "Please upload your resume first."
        ), 404

    # ------------------------------------------------------
    # LOAD PROFILE JSON FIELDS
    # ------------------------------------------------------

    def load_json_field(value):
        if not value:
            return []

        try:
            return json.loads(value)
        except Exception:
            return value

    candidate_profile = {
        "name": user.name or "",
        "email": user.email or "",
        "education": load_json_field(
            student_profile.education
        ),
        "experience": load_json_field(
            student_profile.experience
        ),
        "skills": load_json_field(
            student_profile.skills
        ),
        "projects": load_json_field(
            student_profile.projects
        ),
        "certifications": load_json_field(
            student_profile.certifications
        )
    }

    # ------------------------------------------------------
    # PREPARE SELECTED JOB
    # ------------------------------------------------------

    selected_job = {
        "job_id": job.job_id,
        "job_title": job.title or "",
        "company": job.company or "",
        "category": job.category or "",
        "description": job.description or "",
        "skills": job.skills or "",
        "experience": job.experience or "",
        "education": job.education or "",
        "industry": job.industry or "",
        "location": job.location or "",
        "payrate": job.payrate or ""
    }

    # ------------------------------------------------------
    # GET LATEST M3.1 SKILL GAP ANALYSIS
    # ------------------------------------------------------

    skill_gap = {}

    skill_gap_record = (
        M3SkillGapAnalysis.query
        .filter_by(
            user_id=user_id,
            job_id=str(job.job_id)
        )
        .order_by(
            M3SkillGapAnalysis.created_at.desc()
        )
        .first()
    )

    if skill_gap_record and skill_gap_record.analysis:
        try:
            data = json.loads(
                skill_gap_record.analysis
            )

            if isinstance(data, dict):
                skill_gap = data

        except Exception as e:
            print(
                f"M3.1 SKILL GAP READ ERROR: {e}"
            )

    # ------------------------------------------------------
    # RUN M3.3 INTERVIEW PREPARATION AGENT
    # ------------------------------------------------------

    try:
        result = m3_interview_agent.prepare(
            candidate_profile,
            selected_job,
            skill_gap
        )

    except Exception as e:
        db.session.rollback()

        print(
            f"M3.3 INTERVIEW PREPARATION ERROR: {e}"
        )

        return (
            f"M3.3 Interview Preparation Agent Error: {str(e)}",
            500
        )

    # ------------------------------------------------------
    # SAFETY CHECK
    # ------------------------------------------------------

    if not isinstance(result, dict):
        result = {
            "job_id": job.job_id,
            "job_title": job.title or "",
            "technical_questions": [],
            "resume_questions": [],
            "project_questions": [],
            "role_specific_questions": [],
            "hr_questions": [],
            "preparation_guidance": [],
            "revision_topics": [],
            "skill_gap_preparation": [],
            "error": (
                "Unexpected response from "
                "M3 Interview Preparation Agent."
            )
        }

    # ------------------------------------------------------
    # SAVE M3.3 RESULT TO DATABASE
    # ------------------------------------------------------

    try:
        interview_record = M3InterviewPreparation(
            user_id=user_id,
            job_id=str(job.job_id),
            interview_preparation=json.dumps(
                result,
                ensure_ascii=False
            )
        )

        db.session.add(
            interview_record
        )

        db.session.commit()

        print(
            f"M3.3: Interview preparation saved "
            f"for job {job.job_id}."
        )

    except Exception as e:
        db.session.rollback()

        print(
            f"M3.3 DATABASE ERROR: {e}"
        )

        return (
            f"Error saving M3.3 interview preparation: {str(e)}",
            500
        )

    # ------------------------------------------------------
    # DISPLAY M3.3 RESULT
    # ------------------------------------------------------

    return render_template(
        "m3_interview_page.html",
        user=user,
        result=result,
        selected_job=selected_job
    )


# ==========================================================
# SKILL GAP PAGE
# ==========================================================

@app.route("/skill-gap")
@app.route("/skill-gap/<job_id>")
def skill_gap_page(job_id=None):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    user_id = session["user_id"]


    user = User.query.get(
        user_id
    )


    if user is None:

        session.clear()

        return redirect(
            url_for("login")
        )


    # ------------------------------------------------------
    # GET LATEST AI ANALYSIS
    # ------------------------------------------------------

    analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )


    # ------------------------------------------------------
    # DEFAULT DATA
    # ------------------------------------------------------

    skill_gap = {

        "target_role": "",

        "current_skills": [],

        "required_skills": [],

        "matching_skills": [],

        "missing_skills": [],

        "skills_to_improve": [],

        "recommendations": []

    }


    # ------------------------------------------------------
    # LOAD MILESTONE 3.1 SELECTED-JOB ANALYSIS
    # ------------------------------------------------------

    m3_skill_gap = None
    selected_job = None

    if job_id:
        selected_job = Job.query.filter_by(job_id=str(job_id)).first()

        if selected_job:
            m3_record = (
                M3SkillGapAnalysis.query
                .filter_by(user_id=user_id, job_id=str(selected_job.job_id))
                .order_by(M3SkillGapAnalysis.created_at.desc())
                .first()
            )

            if m3_record and m3_record.analysis:
                try:
                    data = json.loads(m3_record.analysis)
                    if isinstance(data, dict):
                        m3_skill_gap = data
                except Exception as e:
                    print(f"M3.1 SKILL GAP READ ERROR: {e}")

    # ------------------------------------------------------
    # LOAD SKILL GAP ANALYSIS
    # ------------------------------------------------------

    if analysis and analysis.skill_gap:

        try:

            data = json.loads(
                analysis.skill_gap
            )


            if isinstance(data, dict):

                skill_gap.update(
                    data
                )


        except Exception:

            pass


    return render_template(
        "skill_gap_page.html",
        user=user,
        skill_gap=skill_gap,
        m3_skill_gap=m3_skill_gap,
        selected_job=selected_job
    )


## ==========================================================
# INTERVIEW PAGE
# ==========================================================

@app.route("/interview")
def interview_page():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    user = User.query.get(
        user_id
    )

    if user is None:
        session.clear()
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # GET LATEST AI ANALYSIS
    # ------------------------------------------------------

    analysis = (
        AIAnalysis.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
        .first()
    )

    # ------------------------------------------------------
    # DEFAULT INTERVIEW DATA
    # ------------------------------------------------------

    interview = {

        "target_role": "",

        "technical_questions": [],

        "conceptual_questions": [],

        "hr_questions": [],

        "preparation_tips": []

    }

    # ------------------------------------------------------
    # LOAD INTERVIEW DATA FROM DATABASE
    # ------------------------------------------------------

    if analysis and analysis.interview_preparation:

        try:

            data = json.loads(
                analysis.interview_preparation
            )

            if isinstance(data, dict):

                interview.update(
                    data
                )

        except Exception as e:

            print(
                f"INTERVIEW DATA READ ERROR: {e}"
            )

    # ------------------------------------------------------
    # DISPLAY INTERVIEW PAGE
    # ------------------------------------------------------

    return render_template(

        "interview_page.html",

        user=user,

        interview=interview

    )
# ==========================================================
# AI CAREER COACH PAGE
# ==========================================================

@app.route("/career-coach")
def career_coach_page():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    user = User.query.get(
        user_id
    )

    if user is None:
        session.clear()
        return redirect(
            url_for("login")
        )

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    # ------------------------------------------------------
    # GET LATEST AI ANALYSIS
    # ------------------------------------------------------

    analysis = (
        AIAnalysis.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            AIAnalysis.created_at.desc()
        )
        .first()
    )

    # ------------------------------------------------------
    # DEFAULT CAREER COACH DATA
    # ------------------------------------------------------

    career_analysis = {
        "recommended_roles": [],
        "career_paths": [],
        "recommendations": []
    }

    skill_gap = {
        "target_role": "",
        "current_skills": [],
        "required_skills": [],
        "matching_skills": [],
        "missing_skills": [],
        "skills_to_improve": [],
        "recommendations": []
    }

    # ------------------------------------------------------
    # LOAD CAREER ANALYSIS
    # ------------------------------------------------------

    if analysis and analysis.career_recommendations:

        try:

            data = json.loads(
                analysis.career_recommendations
            )

            if isinstance(data, dict):

                career_analysis.update(
                    data
                )

        except Exception as e:

            print(
                f"CAREER COACH CAREER DATA ERROR: {e}"
            )

    # ------------------------------------------------------
    # LOAD SKILL GAP ANALYSIS
    # ------------------------------------------------------

    if analysis and analysis.skill_gap:

        try:

            data = json.loads(
                analysis.skill_gap
            )

            if isinstance(data, dict):

                skill_gap.update(
                    data
                )

        except Exception as e:

            print(
                f"CAREER COACH SKILL DATA ERROR: {e}"
            )

    # ------------------------------------------------------
    # DISPLAY CAREER COACH
    # ------------------------------------------------------

    return render_template(

        "career_coach_page.html",

        user=user,

        student_profile=student_profile,

        career_analysis=career_analysis,

        skill_gap=skill_gap

    )

# ==========================================================
# SETTINGS PAGE
# ==========================================================

@app.route("/settings")
def settings_page():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    user_id = session["user_id"]

    user = User.query.get(
        user_id
    )

    if user is None:
        session.clear()
        return redirect(
            url_for("login")
        )

    return render_template(
        "settings_page.html",
        user=user
    )

# ==========================================================
# MILESTONE 3.4 - AI CAREER COACH CHAT API
# ==========================================================

@app.route(
    "/career-coach/chat",
    methods=["POST"]
)
def career_coach_chat():

    # ------------------------------------------------------
    # 1. CHECK LOGIN
    # ------------------------------------------------------

    if "user_id" not in session:

        return {
            "success": False,
            "error": "Please login first."
        }, 401


    # ------------------------------------------------------
    # 2. GET REQUEST DATA
    # ------------------------------------------------------

    data = request.get_json()

    if not data:

        return {
            "success": False,
            "error": "No message received."
        }, 400


    message = data.get(
        "message",
        ""
    ).strip()


    if not message:

        return {
            "success": False,
            "error": "Please enter a question."
        }, 400


    # ------------------------------------------------------
    # 3. GET LOGGED-IN USER
    # ------------------------------------------------------

    user_id = session["user_id"]

    user = User.query.get(
        user_id
    )


    if user is None:

        session.clear()

        return {
            "success": False,
            "error": "User account not found."
        }, 401


    # ------------------------------------------------------
    # 4. GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = (
        StudentProfile.query
        .filter_by(
            user_id=user_id
        )
        .first()
    )


    # ------------------------------------------------------
    # 5. HELPER TO LOAD JSON DATABASE FIELDS
    # ------------------------------------------------------

    def load_json_field(value):

        if not value:
            return []

        try:

            return json.loads(value)

        except Exception:

            return value


    # ------------------------------------------------------
    # 6. BUILD STUDENT PROFILE
    # ------------------------------------------------------

    profile_information = {

        "name": user.name or "",

        "email": user.email or "",

        "education": [],

        "experience": [],

        "skills": [],

        "projects": [],

        "certifications": []

    }


    if student_profile:

        profile_information["education"] = (
            load_json_field(
                student_profile.education
            )
        )

        profile_information["experience"] = (
            load_json_field(
                student_profile.experience
            )
        )

        profile_information["skills"] = (
            load_json_field(
                student_profile.skills
            )
        )

        profile_information["projects"] = (
            load_json_field(
                student_profile.projects
            )
        )

        profile_information["certifications"] = (
            load_json_field(
                student_profile.certifications
            )
        )


    # ------------------------------------------------------
    # 7. GET USER'S MATCHED JOBS
    #
    # M2 Job-Resume Matching Agent results
    # ------------------------------------------------------

    matched_job_records = (
        JobMatch.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            JobMatch.compatibility_score.desc()
        )
        .limit(10)
        .all()
    )


    matched_jobs = []


    for match in matched_job_records:

        job = Job.query.filter_by(
            job_id=str(match.job_id)
        ).first()


        if job is None:
            continue


        matched_jobs.append({

            "job_id": job.job_id,

            "job_title": job.title or "",

            "company": job.company or "",

            "category": job.category or "",

            "description": job.description or "",

            "skills": job.skills or "",

            "experience": job.experience or "",

            "education": job.education or "",

            "industry": job.industry or "",

            "location": job.location or "",

            "payrate": job.payrate or "",

            "compatibility_score": round(
                float(
                    match.compatibility_score or 0
                ),
                2
            ),

            "matching_skills": load_json_field(
                match.matching_skills
            ),

            "missing_skills": load_json_field(
                match.missing_skills
            ),

            "reasoning": match.reasoning or ""

        })


    # ------------------------------------------------------
    # 8. GET OPTIONAL SELECTED JOB
    #
    # The frontend can send:
    #
    # {
    #     "message": "...",
    #     "job_id": "12345"
    # }
    #
    # ------------------------------------------------------

    selected_job = None

    selected_job_id = data.get(
        "job_id"
    )


    if selected_job_id:

        selected_job_record = (
            Job.query
            .filter_by(
                job_id=str(
                    selected_job_id
                )
            )
            .first()
        )


        if selected_job_record:

            selected_job = {

                "job_id": selected_job_record.job_id,

                "job_title": (
                    selected_job_record.title
                    or ""
                ),

                "company": (
                    selected_job_record.company
                    or ""
                ),

                "category": (
                    selected_job_record.category
                    or ""
                ),

                "description": (
                    selected_job_record.description
                    or ""
                ),

                "skills": (
                    selected_job_record.skills
                    or ""
                ),

                "experience": (
                    selected_job_record.experience
                    or ""
                ),

                "education": (
                    selected_job_record.education
                    or ""
                ),

                "industry": (
                    selected_job_record.industry
                    or ""
                ),

                "location": (
                    selected_job_record.location
                    or ""
                ),

                "payrate": (
                    selected_job_record.payrate
                    or ""
                )

            }


    # ------------------------------------------------------
    # 9. GET LATEST M3.1 SKILL GAP
    # ------------------------------------------------------

    skill_gap = {}


    if selected_job:

        skill_gap_record = (
            M3SkillGapAnalysis.query
            .filter_by(
                user_id=user_id,
                job_id=str(
                    selected_job["job_id"]
                )
            )
            .order_by(
                M3SkillGapAnalysis.created_at.desc()
            )
            .first()
        )


        if (
            skill_gap_record
            and skill_gap_record.analysis
        ):

            try:

                data_value = json.loads(
                    skill_gap_record.analysis
                )


                if isinstance(
                    data_value,
                    dict
                ):

                    skill_gap = data_value


            except Exception as e:

                print(
                    f"M3.1 CAREER COACH READ ERROR: {e}"
                )


    # ------------------------------------------------------
    # 10. GET LATEST M3.2 RESUME/COVER LETTER
    # ------------------------------------------------------

    resume_customization = {}


    if selected_job:

        resume_record = (
            M3ResumeCoverLetter.query
            .filter_by(
                user_id=user_id,
                job_id=str(
                    selected_job["job_id"]
                )
            )
            .order_by(
                M3ResumeCoverLetter.created_at.desc()
            )
            .first()
        )


        if resume_record:

            if resume_record.tailored_resume:

                try:

                    resume_customization = (
                        json.loads(
                            resume_record.tailored_resume
                        )
                    )

                except Exception as e:

                    print(
                        f"M3.2 CAREER COACH READ ERROR: {e}"
                    )


    # ------------------------------------------------------
    # 11. GET LATEST M3.3 INTERVIEW PREPARATION
    # ------------------------------------------------------

    interview_preparation = {}


    if selected_job:

        interview_record = (
            M3InterviewPreparation.query
            .filter_by(
                user_id=user_id,
                job_id=str(
                    selected_job["job_id"]
                )
            )
            .order_by(
                M3InterviewPreparation.created_at.desc()
            )
            .first()
        )


        if (
            interview_record
            and interview_record.interview_preparation
        ):

            try:

                interview_data = json.loads(
                    interview_record.interview_preparation
                )


                if isinstance(
                    interview_data,
                    dict
                ):

                    interview_preparation = (
                        interview_data
                    )


            except Exception as e:

                print(
                    f"M3.3 CAREER COACH READ ERROR: {e}"
                )


    # ------------------------------------------------------
    # 12. GET RETRIEVED JOBS FROM M2 RAG
    #
    # Use FAISS when available.
    # Otherwise use SQL fallback.
    # ------------------------------------------------------

    retrieved_jobs = []


    if job_retrieval_available and job_retrieval_agent:

        try:

            retrieved_jobs = (
                job_retrieval_agent.retrieve_jobs(
                    profile_information,
                    top_k_chunks=15,
                    top_k_jobs=5
                )
            )

            print(
                f"M3.4: Retrieved "
                f"{len(retrieved_jobs)} jobs using FAISS."
            )


        except Exception as e:

            print(
                f"M3.4 FAISS RETRIEVAL ERROR: {e}"
            )

            retrieved_jobs = []


    # ------------------------------------------------------
    # SQL FALLBACK
    # ------------------------------------------------------

    if not retrieved_jobs:

        try:

            retrieved_jobs = (
                fallback_retrieve_jobs(
                    profile_information,
                    top_k_jobs=5
                )
            )

            print(
                f"M3.4: Retrieved "
                f"{len(retrieved_jobs)} jobs using SQL fallback."
            )


        except Exception as e:

            print(
                f"M3.4 SQL RETRIEVAL ERROR: {e}"
            )

            retrieved_jobs = []


    # ------------------------------------------------------
    # 13. LOAD CONVERSATION HISTORY
    #
    # Last 10 messages are supplied to the AI assistant.
    # ------------------------------------------------------

    conversation_records = (
        CareerConversationMessage.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            CareerConversationMessage.created_at.desc()
        )
        .limit(10)
        .all()
    )


    conversation_history = []


    # Reverse because database query is newest first.
    for record in reversed(
        conversation_records
    ):

        conversation_history.append({

            "role": record.role,

            "message": record.message

        })


    # ------------------------------------------------------
    # 14. RUN M3.4 CAREER ASSISTANT
    # ------------------------------------------------------

    try:

        answer = (
            m3_career_assistant_agent.respond(

                student_profile=profile_information,

                user_message=message,

                matched_jobs=matched_jobs,

                selected_job=selected_job,

                skill_gap=skill_gap,

                resume_customization=resume_customization,

                interview_preparation=interview_preparation,

                retrieved_jobs=retrieved_jobs,

                conversation_history=conversation_history

            )
        )


    except Exception as e:

        print(
            f"M3.4 CAREER ASSISTANT ERROR: {e}"
        )

        return {

            "success": False,

            "error": (
                "AI Career Coach could not "
                "generate a response right now."
            )

        }, 500


    # ------------------------------------------------------
    # 15. SAFETY CHECK FOR AI RESPONSE
    # ------------------------------------------------------

    if not answer:

        answer = (
            "I couldn't generate an answer right now."
        )


    # ------------------------------------------------------
    # 16. SAVE USER MESSAGE
    # ------------------------------------------------------

    try:

        user_message_record = (
            CareerConversationMessage(

                user_id=user_id,

                role="user",

                message=message

            )
        )


        db.session.add(
            user_message_record
        )

        db.session.commit()


    except Exception as e:

        db.session.rollback()

        print(
            f"M3.4 USER MESSAGE SAVE ERROR: {e}"
        )


    # ------------------------------------------------------
    # 17. SAVE AI RESPONSE
    # ------------------------------------------------------

    try:

        assistant_message_record = (
            CareerConversationMessage(

                user_id=user_id,

                role="assistant",

                message=str(answer)

            )
        )


        db.session.add(
            assistant_message_record
        )

        db.session.commit()


    except Exception as e:

        db.session.rollback()

        print(
            f"M3.4 ASSISTANT MESSAGE SAVE ERROR: {e}"
        )


    # ------------------------------------------------------
    # 18. RETURN RESPONSE TO WEBSITE
    # ------------------------------------------------------

    print(
        "M3.4 CAREER COACH: Response generated successfully."
    )


    return {

        "success": True,

        "answer": str(answer)

    }
# ==========================================================
# MILESTONE 3 - MOCK INTERVIEW
# ==========================================================

@app.route(
    "/mock-interview/<job_id>",
    methods=["GET"]
)
def mock_interview(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ------------------------------------------------------
    # GET USER
    # ------------------------------------------------------

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # GET SELECTED JOB
    # ------------------------------------------------------

    job = Job.query.filter_by(
        job_id=str(job_id)
    ).first()

    if job is None:
        return "Selected job was not found.", 404

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return (
            "Student profile not found. "
            "Please upload your resume first."
        ), 404

    # ------------------------------------------------------
    # HELPER FUNCTION
    # ------------------------------------------------------

    def load_json_field(value):

        if not value:
            return []

        try:
            return json.loads(value)

        except Exception:
            return value

    # ------------------------------------------------------
    # BUILD CANDIDATE PROFILE
    # ------------------------------------------------------

    candidate_profile = {

        "name": user.name or "",

        "email": user.email or "",

        "education": load_json_field(
            student_profile.education
        ),

        "experience": load_json_field(
            student_profile.experience
        ),

        "skills": load_json_field(
            student_profile.skills
        ),

        "projects": load_json_field(
            student_profile.projects
        ),

        "certifications": load_json_field(
            student_profile.certifications
        )
    }

    # ------------------------------------------------------
    # BUILD SELECTED JOB
    # ------------------------------------------------------

    selected_job = {

        "job_id": job.job_id,

        "job_title": job.title or "",

        "company": job.company or "",

        "category": job.category or "",

        "description": job.description or "",

        "skills": job.skills or "",

        "experience": job.experience or "",

        "education": job.education or "",

        "industry": job.industry or "",

        "location": job.location or "",

        "payrate": job.payrate or ""
    }

    # ------------------------------------------------------
    # CREATE UNIQUE SESSION KEY
    # ------------------------------------------------------

    mock_key = f"mock_interview_{user_id}_{job.job_id}"

    # ------------------------------------------------------
    # START NEW MOCK INTERVIEW
    # ------------------------------------------------------

    if mock_key not in session:

        try:

            question = m3_mock_interview_agent.generate_question(
                candidate_profile,
                selected_job,
                interview_context={
                    "question_number": 1
                },
                previous_questions=[]
            )

        except Exception as e:

            print(
                f"M3 MOCK INTERVIEW QUESTION ERROR: {e}"
            )

            return render_template(
                "m3_mock_interview.html",
                selected_job=selected_job,
                question=None,
                results=[],
                final_summary=None,
                interview_complete=False,
                error=(
                    "Unable to generate the first "
                    f"interview question: {str(e)}"
                )
            )

        session[mock_key] = {

            "question": question,

            "results": [],

            "previous_questions": [],

            "final_summary": None,

            "interview_complete": False
        }

        session.modified = True

    # ------------------------------------------------------
    # GET CURRENT MOCK INTERVIEW STATE
    # ------------------------------------------------------

    interview_state = session.get(
        mock_key,
        {}
    )

    return render_template(

        "m3_mock_interview.html",

        selected_job=selected_job,

        question=interview_state.get(
            "question"
        ),

        results=interview_state.get(
            "results",
            []
        ),

        final_summary=interview_state.get(
            "final_summary"
        ),

        interview_complete=interview_state.get(
            "interview_complete",
            False
        ),

        error=None
    )


# ==========================================================
# M3 MOCK INTERVIEW - SUBMIT ANSWER
# ==========================================================

@app.route(
    "/mock-interview/<job_id>/answer",
    methods=["POST"]
)
def mock_interview_answer(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ------------------------------------------------------
    # GET USER
    # ------------------------------------------------------

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # GET SELECTED JOB
    # ------------------------------------------------------

    job = Job.query.filter_by(
        job_id=str(job_id)
    ).first()

    if job is None:
        return "Selected job was not found.", 404

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return (
            "Student profile not found. "
            "Please upload your resume first."
        ), 404

    # ------------------------------------------------------
    # HELPER
    # ------------------------------------------------------

    def load_json_field(value):

        if not value:
            return []

        try:
            return json.loads(value)

        except Exception:
            return value

    # ------------------------------------------------------
    # BUILD CANDIDATE PROFILE
    # ------------------------------------------------------

    candidate_profile = {

        "name": user.name or "",

        "email": user.email or "",

        "education": load_json_field(
            student_profile.education
        ),

        "experience": load_json_field(
            student_profile.experience
        ),

        "skills": load_json_field(
            student_profile.skills
        ),

        "projects": load_json_field(
            student_profile.projects
        ),

        "certifications": load_json_field(
            student_profile.certifications
        )
    }

    # ------------------------------------------------------
    # BUILD JOB
    # ------------------------------------------------------

    selected_job = {

        "job_id": job.job_id,

        "job_title": job.title or "",

        "company": job.company or "",

        "category": job.category or "",

        "description": job.description or "",

        "skills": job.skills or "",

        "experience": job.experience or "",

        "education": job.education or "",

        "industry": job.industry or "",

        "location": job.location or "",

        "payrate": job.payrate or ""
    }

    # ------------------------------------------------------
    # GET MOCK INTERVIEW STATE
    # ------------------------------------------------------

    mock_key = f"mock_interview_{user_id}_{job.job_id}"

    interview_state = session.get(
        mock_key
    )

    if not interview_state:

        return redirect(
            url_for(
                "mock_interview",
                job_id=job.job_id
            )
        )

    # ------------------------------------------------------
    # CHECK IF ALREADY COMPLETE
    # ------------------------------------------------------

    if interview_state.get(
        "interview_complete",
        False
    ):

        return redirect(
            url_for(
                "mock_interview",
                job_id=job.job_id
            )
        )

    # ------------------------------------------------------
    # GET STUDENT ANSWER
    # ------------------------------------------------------

    answer = request.form.get(
        "answer",
        ""
    ).strip()

    if not answer:

        return render_template(

            "m3_mock_interview.html",

            selected_job=selected_job,

            question=interview_state.get(
                "question"
            ),

            results=interview_state.get(
                "results",
                []
            ),

            final_summary=interview_state.get(
                "final_summary"
            ),

            interview_complete=False,

            error="Please enter your answer before submitting."
        )

    # ------------------------------------------------------
    # GET CURRENT QUESTION
    # ------------------------------------------------------

    current_question = interview_state.get(
        "question"
    )

    if not current_question:

        return redirect(
            url_for(
                "mock_interview",
                job_id=job.job_id
            )
        )

    # ------------------------------------------------------
    # EVALUATE ANSWER
    # ------------------------------------------------------

    try:

        evaluation = m3_mock_interview_agent.evaluate_answer(

            candidate_profile,

            selected_job,

            current_question.get(
                "question",
                ""
            ),

            answer,

            interview_context={
                "question_number":
                    len(
                        interview_state.get(
                            "results",
                            []
                        )
                    ) + 1
            }
        )

    except Exception as e:

        print(
            f"M3 MOCK INTERVIEW EVALUATION ERROR: {e}"
        )

        return render_template(

            "m3_mock_interview.html",

            selected_job=selected_job,

            question=current_question,

            results=interview_state.get(
                "results",
                []
            ),

            final_summary=None,

            interview_complete=False,

            error=(
                "Unable to evaluate your answer: "
                f"{str(e)}"
            )
        )

    # ------------------------------------------------------
    # SAVE CURRENT RESULT
    # ------------------------------------------------------

    result_item = {

        "question": current_question.get(
            "question",
            ""
        ),

        "question_type": current_question.get(
            "question_type",
            ""
        ),

        "topic": current_question.get(
            "topic",
            ""
        ),

        "answer": answer,

        "evaluation": evaluation
    }

    results = interview_state.get(
        "results",
        []
    )

    results.append(
        result_item
    )

    # ------------------------------------------------------
    # SAVE PREVIOUS QUESTION
    # ------------------------------------------------------

    previous_questions = interview_state.get(
        "previous_questions",
        []
    )

    previous_questions.append(
        current_question.get(
            "question",
            ""
        )
    )

    # ------------------------------------------------------
    # FIVE QUESTION LIMIT
    # ------------------------------------------------------

    if len(results) >= 5:

        interview_state["question"] = None

        interview_state["results"] = results

        interview_state[
            "previous_questions"
        ] = previous_questions

        interview_state[
            "interview_complete"
        ] = False

        interview_state[
            "final_summary"
        ] = None

        session[mock_key] = interview_state

        session.modified = True

        return redirect(
            url_for(
                "mock_interview",
                job_id=job.job_id
            )
        )

    # ------------------------------------------------------
    # GENERATE NEXT QUESTION
    # ------------------------------------------------------

    try:

        next_question = (
            m3_mock_interview_agent.generate_question(

                candidate_profile,

                selected_job,

                interview_context={
                    "question_number":
                        len(results) + 1,

                    "completed_questions":
                        len(results)
                },

                previous_questions=
                    previous_questions
            )
        )

    except Exception as e:

        print(
            f"M3 MOCK INTERVIEW NEXT QUESTION ERROR: {e}"
        )

        interview_state["question"] = None

        interview_state["results"] = results

        interview_state[
            "previous_questions"
        ] = previous_questions

        session[mock_key] = interview_state

        session.modified = True

        return render_template(

            "m3_mock_interview.html",

            selected_job=selected_job,

            question=None,

            results=results,

            final_summary=None,

            interview_complete=False,

            error=(
                "Your answer was evaluated, "
                "but the next question could not be generated: "
                f"{str(e)}"
            )
        )

    # ------------------------------------------------------
    # UPDATE SESSION
    # ------------------------------------------------------

    interview_state["question"] = next_question

    interview_state["results"] = results

    interview_state[
        "previous_questions"
    ] = previous_questions

    session[mock_key] = interview_state

    session.modified = True

    return redirect(
        url_for(
            "mock_interview",
            job_id=job.job_id
        )
    )


# ==========================================================
# M3 MOCK INTERVIEW - FINISH
# ==========================================================

@app.route(
    "/mock-interview/<job_id>/finish",
    methods=["POST"]
)
def finish_mock_interview(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ------------------------------------------------------
    # GET USER
    # ------------------------------------------------------

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # GET SELECTED JOB
    # ------------------------------------------------------

    job = Job.query.filter_by(
        job_id=str(job_id)
    ).first()

    if job is None:
        return "Selected job was not found.", 404

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return (
            "Student profile not found. "
            "Please upload your resume first."
        ), 404

    # ------------------------------------------------------
    # HELPER
    # ------------------------------------------------------

    def load_json_field(value):

        if not value:
            return []

        try:
            return json.loads(value)

        except Exception:
            return value

    # ------------------------------------------------------
    # BUILD CANDIDATE PROFILE
    # ------------------------------------------------------

    candidate_profile = {

        "name": user.name or "",

        "email": user.email or "",

        "education": load_json_field(
            student_profile.education
        ),

        "experience": load_json_field(
            student_profile.experience
        ),

        "skills": load_json_field(
            student_profile.skills
        ),

        "projects": load_json_field(
            student_profile.projects
        ),

        "certifications": load_json_field(
            student_profile.certifications
        )
    }

    # ------------------------------------------------------
    # BUILD JOB
    # ------------------------------------------------------

    selected_job = {

        "job_id": job.job_id,

        "job_title": job.title or "",

        "company": job.company or "",

        "category": job.category or "",

        "description": job.description or "",

        "skills": job.skills or "",

        "experience": job.experience or "",

        "education": job.education or "",

        "industry": job.industry or "",

        "location": job.location or "",

        "payrate": job.payrate or ""
    }

    # ------------------------------------------------------
    # GET MOCK INTERVIEW STATE
    # ------------------------------------------------------

    mock_key = f"mock_interview_{user_id}_{job.job_id}"

    interview_state = session.get(
        mock_key
    )

    if not interview_state:

        return redirect(
            url_for(
                "mock_interview",
                job_id=job.job_id
            )
        )

    results = interview_state.get(
        "results",
        []
    )

    # ------------------------------------------------------
    # GENERATE FINAL SUMMARY
    # ------------------------------------------------------

    try:

        final_summary = (
            m3_mock_interview_agent.generate_final_summary(

                candidate_profile,

                selected_job,

                results
            )
        )

    except Exception as e:

        print(
            f"M3 MOCK INTERVIEW SUMMARY ERROR: {e}"
        )

        return render_template(

            "m3_mock_interview.html",

            selected_job=selected_job,

            question=interview_state.get(
                "question"
            ),

            results=results,

            final_summary=None,

            interview_complete=False,

            error=(
                "Unable to generate the final "
                f"interview summary: {str(e)}"
            )
        )

    # ------------------------------------------------------
    # MARK INTERVIEW AS COMPLETE
    # ------------------------------------------------------

    interview_state["question"] = None

    interview_state["results"] = results

    interview_state[
        "final_summary"
    ] = final_summary

    interview_state[
        "interview_complete"
    ] = True

    session[mock_key] = interview_state

    session.modified = True

    return redirect(
        url_for(
            "mock_interview",
            job_id=job.job_id
        )
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================================
# RUN FLASK APPLICATION
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )