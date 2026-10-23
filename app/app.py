import os
import json
import time
import ast

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from datetime import datetime
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
    CareerConversation,
    CareerConversationMessage,
    Application
)
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from services.gemini_service import GeminiService
from services.document_generator import DocumentGenerator

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
from services.document_generator import DocumentGenerator
from flask_mail import Mail, Message


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
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Local data directory; can be changed on the hosting server.
PERSISTENT_DIR = os.getenv(
    "CAREERAI_DATA_DIR",
    os.path.join(BASE_DIR, "careerai_data")
)
os.makedirs(PERSISTENT_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(PERSISTENT_DIR, "uploads")
LOCAL_DATA_DIR = PERSISTENT_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)

PROFILE_FILE = os.path.join(
    LOCAL_DATA_DIR, "candidate_profile.json"
)

# ==========================================================
# DOCUMENT GENERATION
# ==========================================================

GENERATED_DOCUMENTS_DIR = os.path.join(
    PERSISTENT_DIR, "generated_documents"
)
os.makedirs(GENERATED_DOCUMENTS_DIR, exist_ok=True)

document_generator = DocumentGenerator(
    GENERATED_DOCUMENTS_DIR
)

# ==========================================================
# CREATE FLASK APPLICATION
# ==========================================================

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "careerai-development-secret"
)

# ==========================================================
# EMAIL CONFIGURATION
# ==========================================================

app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)


# ==========================================================
# SERVER-SIDE SESSION CONFIGURATION
# ==========================================================

SESSION_DIR = os.path.join(PERSISTENT_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = SESSION_DIR
app.config["SESSION_PERMANENT"] = False

Session(app)

# ==========================================================
# DATABASE CONFIGURATION
# ==========================================================

DATABASE_PATH = os.path.join(
    PERSISTENT_DIR, "careerai.db"
)

database_url = os.getenv("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///" + DATABASE_PATH.replace("\\", "/")
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"timeout": 30}
    }

db.init_app(app)

# ==========================================================
# MILESTONE 2 AGENTS
# ==========================================================

job_retrieval_agent = None
job_retrieval_available = False
gemini_service = GeminiService()
try:
    from agents.job_retrieval_agent import JobRetrievalAgent
    job_retrieval_agent = JobRetrievalAgent(gemini_service)
    job_retrieval_available = True
    print("M2: Job Retrieval Agent loaded successfully.")
except Exception as e:
    print("M2: FAISS/Job Retrieval Agent unavailable.")
    print(f"M2 RETRIEVAL ERROR: {e}")

job_matching_agent = JobMatchingAgent()

# ==========================================================
# MILESTONE 3.1 AGENT
# ==========================================================

resume_agent = ResumeAgent(gemini_service)
career_agent = CareerAgent(gemini_service)

skill_gap_agent = SkillGapAgent(gemini_service)
interview_agent = InterviewAgent(gemini_service)


m3_skill_gap_agent = M3SkillGapAgent(gemini_service)
m3_resume_cover_letter_agent = M3ResumeCoverLetterAgent(gemini_service)
m3_interview_agent = M3InterviewAgent(gemini_service)
m3_career_assistant_agent = M3CareerAssistantAgent(gemini_service)
m3_mock_interview_agent = M3MockInterviewAgent(gemini_service)
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

    # Candidate identity comes from the uploaded resume/profile,
    # not from the login account.
    student_profile.candidate_name = candidate_profile.get(
        "name",
        ""
    ) or ""

    student_profile.candidate_email = candidate_profile.get(
        "email",
        ""
    ) or ""


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
            retrieval_score=float(
            job.get("retrieval_score", 0)
            ),

            retrieval_rank=int(
            job.get("retrieval_rank", 0)
             ),

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
        return render_template("login.html")

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

    # Send login-success email
    try:
        msg = Message(
            subject="Successful Login - AI Career Companion Agent",
            recipients=[user.email],
            body=(
                f"Hello {user.name},\n\n"
                "You have successfully logged in to "
                "AI Career Companion Agent.\n\n"
                "If this wasn't you, please secure your password.\n\n"
                "Regards,\n"
                "AI Career Companion Agent Team"
            )
        )
        mail.send(msg)

    except Exception:
        app.logger.exception(
            "Login notification email could not be sent."
        )

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
# M4.3 - REUSABLE ROUTE HELPERS
# ==========================================================

def get_current_user():
    """Return the logged-in user or None."""
    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.get(user_id)


def load_json_field(value, default=None):
    """Safely convert a JSON database field into Python data."""
    if default is None:
        default = []

    if not value:
        return default

    try:
        return json.loads(value)

    except (json.JSONDecodeError, TypeError):
        return default


def build_candidate_profile(student_profile):
    """Convert StudentProfile database data into agent-ready format."""

    if not student_profile:
        return None

    return {
        "name": student_profile.candidate_name or "",
        "email": student_profile.candidate_email or "",
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


def build_job_data(job):
    """Convert Job database object into agent-ready dictionary."""

    if not job:
        return None

    return {
        "job_id": job.job_id,
        "job_title": job.title or "",
        "jobtitle": job.title or "",
        "company": job.company or "",
        "category": job.category or "",
        "description": job.description or "",
        "jobdescription": job.description or "",
        "skills": job.skills or "",
        "experience": job.experience or "",
        "education": job.education or "",
        "industry": job.industry or "",
        "location": job.location or "",
        "payrate": job.payrate or ""
    }

# ==========================================================
# SAFE JSON LOADER
# ==========================================================

def safe_json_load(value, default=None):

    if default is None:
        default = {}

    if not value:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)

    except (json.JSONDecodeError, TypeError, ValueError):
        return default

# ==========================================================
# HOME / RESUME PROCESSING
# ==========================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)

def profile():

   if request.method == "GET":
    return render_template("landing.html")

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
        rag_start_time = time.perf_counter()

        try:
            retrieved_jobs = job_retrieval_agent.retrieve_jobs(
                candidate_profile,
                top_k_chunks=15,
                top_k_jobs=5
            )
            print(f"M2: Retrieved {len(retrieved_jobs)} jobs.")
            rag_end_time = time.perf_counter()

            rag_retrieval_time = (
             rag_end_time - rag_start_time
            )

            print(
            f"M4.3 RAG RETRIEVAL TIME: "
            f"{rag_retrieval_time:.3f} seconds"
            )

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

    # ------------------------------------------------------
    # 1. CHECK LOGIN
    # ------------------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # ------------------------------------------------------
    # 2. GET USER
    # ------------------------------------------------------

    user = User.query.get(user_id)

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------
    # 3. GET LATEST USER DATA
    # ------------------------------------------------------

    resume_record = (
        Resume.query
        .filter_by(user_id=user_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )

    student_profile = (
        StudentProfile.query
        .filter_by(user_id=user_id)
        .first()
    )

    ai_analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )

    job_matches = (
        JobMatch.query
        .filter_by(user_id=user_id)
        .order_by(JobMatch.compatibility_score.desc())
        .all()
    )

    # ------------------------------------------------------
    # 4. START WITH EMPTY PROFILE
    # ------------------------------------------------------

    profile_data = get_empty_profile()

    # ------------------------------------------------------
    # 5. LOAD STUDENT PROFILE
    # ------------------------------------------------------

    if student_profile:

        candidate_name = (
            student_profile.candidate_name or ""
        )

        candidate_email = (
            student_profile.candidate_email or ""
        )

        profile_data["student_profile"]["name"] = (
            candidate_name
        )

        profile_data["student_profile"]["email"] = (
            candidate_email
        )

        profile_data["resume"]["llm_extracted_profile"]["name"] = (
            candidate_name
        )

        profile_data["resume"]["llm_extracted_profile"]["email"] = (
            candidate_email
        )

        # Use the helper function added earlier
        education = load_json_field(
            student_profile.education
        )

        experience = load_json_field(
            student_profile.experience
        )

        skills = load_json_field(
            student_profile.skills
        )

        projects = load_json_field(
            student_profile.projects
        )

        certifications = load_json_field(
            student_profile.certifications
        )

        profile_data["student_profile"]["education"] = education
        profile_data["student_profile"]["experience"] = experience
        profile_data["student_profile"]["skills"] = skills
        profile_data["student_profile"]["projects"] = projects
        profile_data["student_profile"]["certifications"] = certifications

        # Keep the same information inside resume profile
        llm_profile = profile_data["resume"]["llm_extracted_profile"]

        llm_profile["education"] = education
        llm_profile["experience"] = experience
        llm_profile["skills"] = skills
        llm_profile["projects"] = projects
        llm_profile["certifications"] = certifications

    # ------------------------------------------------------
    # 6. LOAD LATEST RESUME
    # ------------------------------------------------------

    if resume_record:

        profile_data["resume"]["filename"] = (
            resume_record.filename or ""
        )

        profile_data["resume"]["extracted_text"] = (
            resume_record.resume_text or ""
        )

    # ------------------------------------------------------
    # 7. LOAD AI ANALYSIS
    # ------------------------------------------------------

    if ai_analysis:

        profile_data["resume_analysis"] = load_json_field(
            ai_analysis.resume_analysis
        )

        career_data = load_json_field(
            ai_analysis.career_recommendations
        )

        if isinstance(career_data, dict):

            profile_data["career_analysis"] = (
                career_data
            )

        else:

            profile_data["career_analysis"] = {
                "recommended_roles": career_data
            }

        profile_data["skill_gap_analysis"] = (
            load_json_field(
                ai_analysis.skill_gap
            )
        )

        profile_data["interview_analysis"] = (
            load_json_field(
                ai_analysis.interview_preparation
            )
        )

    # ======================================================
    # 8. OPTIMIZED JOB LOOKUP
    # ======================================================
    #
    # OLD:
    #
    # for match in job_matches:
    #     Job.query.filter_by(...)
    #
    # This creates one database query for every match.
    #
    # NEW:
    # Get all required jobs in ONE database query.
    # ======================================================

    matched_jobs = []

    if job_matches:

        job_ids = [
            str(match.job_id)
            for match in job_matches
        ]

        jobs = (
            Job.query
            .filter(
                Job.job_id.in_(job_ids)
            )
            .all()
        )

        # Create lookup dictionary
        jobs_by_id = {
            str(job.job_id): job
            for job in jobs
        }

        # --------------------------------------------------
        # BUILD MATCHED JOBS
        # --------------------------------------------------

        for match in job_matches:

            job = jobs_by_id.get(
                str(match.job_id)
            )

            if job is None:
                continue

            matching_skills = load_json_field(
                match.matching_skills
            )

            missing_skills = load_json_field(
                match.missing_skills
            )

            try:

                compatibility_score = round(
                    float(
                        match.compatibility_score or 0
                    ),
                    2
                )

            except (TypeError, ValueError):

                compatibility_score = 0

            matched_jobs.append({

                "jobid": job.job_id,

                "job_title": (
                    job.title or
                    "Job Opportunity"
                ),

                "title": (
                    job.title or
                    "Job Opportunity"
                ),

                "company": (
                    job.company or
                    "Company"
                ),

                "category": (
                    job.category or ""
                ),

                "description": (
                    job.description or ""
                ),

                "skills": (
                    job.skills or ""
                ),

                "experience": (
                    job.experience or ""
                ),

                "education": (
                    job.education or ""
                ),

                "industry": (
                    job.industry or ""
                ),

                "location": (
                    job.location or ""
                ),

                "payrate": (
                    job.payrate or ""
                ),

                "compatibility_score": (
                    compatibility_score
                ),
                "retrieval_score": (
                match.retrieval_score
                if hasattr(match, "retrieval_score")
                else 0
                ),

                "retrieval_rank": (
                match.retrieval_rank
                if hasattr(match, "retrieval_rank")
                else 0
                ),

                "matching_skills": (
                    matching_skills
                ),

                "missing_skills": (
                    missing_skills
                ),

                "reasoning": (
                    match.reasoning or ""
                )

            })

    # ------------------------------------------------------
    # 9. STORE JOB RESULTS
    # ------------------------------------------------------

    profile_data["job_retrieval_analysis"] = {

        "retrieved_jobs": matched_jobs,

        "number_of_jobs": len(
            matched_jobs
        )

    }

    profile_data["job_matching_analysis"] = {

        "matched_jobs": matched_jobs

    }

    # ------------------------------------------------------
    # 10. DISPLAY DASHBOARD
    # ------------------------------------------------------

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
    # GET OR CREATE STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = (
        StudentProfile.query
        .filter_by(user_id=user_id)
        .first()
    )

    if student_profile is None:

        student_profile = StudentProfile(
            user_id=user_id,
            education=json.dumps([]),
            experience=json.dumps([]),
            skills=json.dumps([]),
            projects=json.dumps([]),
            certifications=json.dumps([])
        )

        try:

            db.session.add(student_profile)
            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print(
                f"PROFILE CREATION ERROR: {e}"
            )

            return (
                "Unable to create student profile.",
                500
            )

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
        # CONVERT FORM DATA INTO LISTS
        # --------------------------------------------------

        education_list = (
            [education]
            if education
            else []
        )

        experience_list = (
            [experience]
            if experience
            else []
        )

        skills_list = [
            skill.strip()
            for skill in skills.split(",")
            if skill.strip()
        ]

        projects_list = (
            [projects]
            if projects
            else []
        )

        certifications_list = [
            certification.strip()
            for certification in certifications.split(",")
            if certification.strip()
        ]

        # --------------------------------------------------
        # SAVE PROFILE DATA
        # --------------------------------------------------

        student_profile.education = json.dumps(
            education_list,
            ensure_ascii=False
        )

        student_profile.experience = json.dumps(
            experience_list,
            ensure_ascii=False
        )

        student_profile.skills = json.dumps(
            skills_list,
            ensure_ascii=False
        )

        student_profile.projects = json.dumps(
            projects_list,
            ensure_ascii=False
        )

        student_profile.certifications = json.dumps(
            certifications_list,
            ensure_ascii=False
        )

        # --------------------------------------------------
        # COMMIT CHANGES
        # --------------------------------------------------

        try:

            db.session.commit()

            print(
                f"PROFILE UPDATED: user_id={user_id}"
            )

        except Exception as e:

            db.session.rollback()

            print(
                f"PROFILE UPDATE ERROR: {e}"
            )

            return (
                "Unable to save profile changes.",
                500
            )

        # --------------------------------------------------
        # POST → REDIRECT → GET
        # --------------------------------------------------

        return redirect(
            url_for("profile_page")
        )

    # ======================================================
    # LOAD JSON FIELD
    # ======================================================

    def load_json_list(value):

        if not value:
            return []

        try:

            data = json.loads(value)

            if isinstance(data, list):
                return data

            return [data]

        except (json.JSONDecodeError, TypeError):

            return []

    # ======================================================
    # PREPARE PROFILE DATA
    # ======================================================

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

    # ======================================================
    # DISPLAY PROFILE PAGE
    # ======================================================

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

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

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
    # GET LATEST RESUME
    # ------------------------------------------------------

    resume = (
        Resume.query
        .filter_by(user_id=user_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
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
    # DEFAULT RESUME ANALYSIS
    # ------------------------------------------------------

    resume_analysis = {}

    if analysis and analysis.resume_analysis:

        resume_analysis = safe_json_load(
            analysis.resume_analysis,
            {}
        )

        if not isinstance(resume_analysis, dict):
            resume_analysis = {}

    # ------------------------------------------------------
    # DISPLAY RESUME PAGE
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

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
    # GET LATEST CAREER ANALYSIS
    # ------------------------------------------------------

    analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )

    # ------------------------------------------------------
    # DEFAULT CAREER DATA
    # ------------------------------------------------------

    career_analysis = {
        "recommended_roles": [],
        "career_paths": [],
        "recommendations": []
    }

    # ------------------------------------------------------
    # LOAD CAREER ANALYSIS
    # ------------------------------------------------------

    if analysis and analysis.career_recommendations:

        data = safe_json_load(
            analysis.career_recommendations,
            {}
        )

        if isinstance(data, dict):
            career_analysis.update(data)

    # ------------------------------------------------------
    # NORMALIZE RECOMMENDED ROLES
    # ------------------------------------------------------

    roles = career_analysis.get(
        "recommended_roles",
        []
    )

    normalized_roles = []

    if isinstance(roles, list):

        for role in roles:

            # Already a dictionary
            if isinstance(role, dict):

                normalized_roles.append(role)
                continue

            # Dictionary stored as a JSON/Python string
            if isinstance(role, str):

                parsed_role = safe_json_load(
                    role,
                    None
                )

                if isinstance(parsed_role, dict):

                    normalized_roles.append(
                        parsed_role
                    )

    career_analysis["recommended_roles"] = normalized_roles

    # ------------------------------------------------------
    # RENDER CAREER PAGE
    # ------------------------------------------------------

    return render_template(
        "career_page.html",
        user=user,
        career_analysis=career_analysis
    )
# ==========================================================
# OPPORTUNITIES PAGE
# ==========================================================

@app.route("/opportunities")
def opportunities_page():

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = StudentProfile.query.filter_by(
        user_id=user_id
    ).first()

    if student_profile is None:
        return render_template(
            "opportunities_page.html",
            opportunities=[],
            matched_jobs=[],
            number_of_jobs=0
        )

    # ------------------------------------------------------
    # HELPER TO LOAD JSON FIELDS
    # ------------------------------------------------------

    def load_profile_field(value):

        if not value:
            return []

        if isinstance(value, (list, tuple, set)):
            return list(value)

        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return parsed

            if isinstance(parsed, dict):
                return [parsed]

            return [parsed]

        except Exception:

            return [str(value)]

    # ------------------------------------------------------
    # BUILD CANDIDATE PROFILE
    # ------------------------------------------------------

    candidate_profile = {

        "name":
            student_profile.candidate_name or "",

        "email":
            student_profile.candidate_email or "",

        "education":
            load_profile_field(
                student_profile.education
            ),

        "experience":
            load_profile_field(
                student_profile.experience
            ),

        "skills":
            load_profile_field(
                student_profile.skills
            ),

        "projects":
            load_profile_field(
                student_profile.projects
            ),

        "certifications":
            load_profile_field(
                student_profile.certifications
            )
    }

    print(
        "M2: Building job matches for user",
        user_id
    )

    # ======================================================
    # MILESTONE 2 - FAISS JOB RETRIEVAL
    # ======================================================

    retrieved_jobs = []

    retrieval_error = ""

    if (
        job_retrieval_available
        and
        job_retrieval_agent is not None
    ):

        try:

            retrieved_jobs = (
                job_retrieval_agent.retrieve_jobs(
                    candidate_profile,
                    top_k_chunks=15,
                    top_k_jobs=5
                )
            )

            print(
                f"M2: Retrieved "
                f"{len(retrieved_jobs)} jobs using FAISS."
            )

        except Exception as e:

            retrieval_error = str(e)

            print(
                f"M2 RETRIEVAL ERROR: {e}"
            )

    # ======================================================
    # FALLBACK
    # ======================================================

    if not retrieved_jobs:

        try:

            retrieved_jobs = (
                fallback_retrieve_jobs(
                    candidate_profile,
                    top_k_jobs=5
                )
            )

            print(
                f"M2 FALLBACK: Retrieved "
                f"{len(retrieved_jobs)} jobs."
            )

        except Exception as e:

            print(
                f"M2 FALLBACK ERROR: {e}"
            )

            retrieved_jobs = []

    # ======================================================
    # CLEAR OLD MATCHES
    #
    # This prevents duplicate JobMatch records every time
    # the Opportunities page is opened.
    # ======================================================

    try:

        JobMatch.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print(
            f"M2 JOBMATCH CLEANUP ERROR: {e}"
        )

    # ======================================================
    # CALCULATE JOB MATCHING
    # ======================================================

    opportunities = []

    for retrieved_job in retrieved_jobs:

        try:

            job_id = str(
                retrieved_job.get(
                    "jobid",
                    ""
                )
            )

            if not job_id:
                continue

            # ------------------------------------------------
            # Find the corresponding Job database record
            # ------------------------------------------------

            job = Job.query.filter_by(
                job_id=job_id
            ).first()

            if job is None:

                print(
                    f"M2: Job {job_id} "
                    f"not found in database."
                )

                continue

            # ------------------------------------------------
            # Calculate compatibility
            # ------------------------------------------------

            match_result = (
                job_matching_agent
                .calculate_compatibility_score(
                    candidate_profile,
                    retrieved_job
                )
            )

            compatibility_score = float(
                match_result.get(
                    "compatibility_score",
                    0
                )
            )

            matching_skills = (
                match_result.get(
                    "matching_skills",
                    []
                )
            )

            missing_skills = (
                match_result.get(
                    "missing_skills",
                    []
                )
            )

            # ------------------------------------------------
            # Build reasoning
            # ------------------------------------------------

            skill_score = match_result.get(
                "skill_score",
                0
            )

            education_score = match_result.get(
                "education_score",
                0
            )

            experience_score = match_result.get(
                "experience_score",
                0
            )

            reasoning = (
                f"Compatibility is based on "
                f"skills ({skill_score}%), "
                f"education ({education_score}%), "
                f"and experience ({experience_score}%). "
                f"Matching skills: "
                f"{', '.join(matching_skills) if matching_skills else 'None'}. "
                f"Missing skills: "
                f"{', '.join(missing_skills) if missing_skills else 'None'}."
            )

            # ==================================================
            # SAVE JOB MATCH
            # ==================================================

            job_match = JobMatch(

                user_id=user_id,

                job_id=job_id,

                compatibility_score=
                    compatibility_score,

                matching_skills=
                    json.dumps(
                        matching_skills
                    ),

                missing_skills=
                    json.dumps(
                        missing_skills
                    ),

                reasoning=reasoning
            )

            db.session.add(
                job_match
            )

            # ==================================================
            # PREPARE OPPORTUNITY FOR UI
            # ==================================================

            opportunities.append({

                "jobid":
                    job.job_id,

                "title":
                    job.title or "Job Opportunity",

                "company":
                    job.company or "Company",

                "category":
                    job.category or "",

                "description":
                    job.description or "",

                "skills":
                    job.skills or "",

                "experience":
                    job.experience or "",

                "education":
                    job.education or "",

                "industry":
                    job.industry or "",

                "location":
                    job.location or "",

                "payrate":
                    job.payrate or "",

                "compatibility_score":
                    compatibility_score,

                "matching_skills":
                    matching_skills,

                "missing_skills":
                    missing_skills,

                "reasoning":
                    reasoning,

                "skill_gap_url":
                    url_for(
                        "analyze_skill_gap",
                        job_id=job.job_id
                    )
            })

            print(
                f"M2 MATCH: "
                f"{job.title} -> "
                f"{compatibility_score}%"
            )

        except Exception as e:

            print(
                f"M2 MATCHING ERROR "
                f"for job "
                f"{retrieved_job.get('jobid')}: "
                f"{e}"
            )

    # ======================================================
    # SAVE ALL MATCHES
    # ======================================================

    try:

        db.session.commit()

        print(
            f"M2: Saved "
            f"{len(opportunities)} JobMatch records."
        )

    except Exception as e:

        db.session.rollback()

        print(
            f"M2 DATABASE ERROR: {e}"
        )

        opportunities = []

    # ======================================================
    # SORT BY COMPATIBILITY
    # ======================================================

    opportunities.sort(
        key=lambda item:
            item.get(
                "compatibility_score",
                0
            ),
        reverse=True
    )

    # ======================================================
    # DISPLAY OPPORTUNITIES
    # ======================================================

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
        "name": student_profile.candidate_name or "",
        "email": student_profile.candidate_email or "",
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
# GENERATED DOCUMENT DOWNLOAD
# ==========================================================

@app.route("/download-document/<path:filename>")
def download_document(filename):
    if "user_id" not in session:
        return redirect(url_for("login"))

    safe_filename = os.path.basename(filename)

    file_path = os.path.join(
        GENERATED_DOCUMENTS_DIR,
        safe_filename
    )

    if not os.path.isfile(file_path):
        return "Document not found", 404

    return send_file(
        file_path,
        as_attachment=True
    )


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
        "name": student_profile.candidate_name or "",
        "email": student_profile.candidate_email or "",
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
    # GENERATE M3.2 DOCUMENTS
    # ------------------------------------------------------

    try:

        resume_docx_path = document_generator.generate_resume_docx(
            candidate_profile,
            selected_job,
            result
        )

        resume_pdf_path = document_generator.generate_resume_pdf(
            candidate_profile,
            selected_job,
            result
        )

        cover_letter_docx_path = document_generator.generate_cover_letter_docx(
            candidate_profile,
            selected_job,
            result
        )

        cover_letter_pdf_path = document_generator.generate_cover_letter_pdf(
            candidate_profile,
            selected_job,
            result
        )

        print(
            f"M3.2: Documents generated successfully "
            f"for job {job.job_id}."
        )

    except Exception as e:

        print(
            f"M3.2 DOCUMENT GENERATION ERROR: {e}"
        )

        resume_docx_path = None
        resume_pdf_path = None
        cover_letter_docx_path = None
        cover_letter_pdf_path = None

    # ------------------------------------------------------
    # DISPLAY M3.2 RESULT
    # ------------------------------------------------------

    return render_template(
        "resume_customization_page.html",
        user=user,
        result=result,
        selected_job=selected_job,
        candidate_profile=candidate_profile,
        resume_docx_path=(
            os.path.basename(resume_docx_path)
            if resume_docx_path
            else None
        ),
        resume_pdf_path=(
            os.path.basename(resume_pdf_path)
            if resume_pdf_path
            else None
        ),
        cover_letter_docx_path=(
            os.path.basename(cover_letter_docx_path)
            if cover_letter_docx_path
            else None
        ),
        cover_letter_pdf_path=(
            os.path.basename(cover_letter_pdf_path)
            if cover_letter_pdf_path
            else None
        )
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
        "name": student_profile.candidate_name or "",
        "email": student_profile.candidate_email or "",
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
# CAREER COACH — NEW CHAT
# ==========================================================

@app.route(
    "/career-coach/new-chat",
    methods=["POST"]
)
def new_career_chat():

    if "user_id" not in session:
        return {
            "success": False,
            "error": "Please login first."
        }, 401

    user_id = session["user_id"]

    conversation = CareerConversation(
        user_id=user_id,
        title="New Chat"
    )

    db.session.add(conversation)
    db.session.commit()

    return {
        "success": True,
        "conversation_id": conversation.id,
        "title": conversation.title
    }
# ==========================================================
# CAREER COACH — CHAT HISTORY
# ==========================================================

@app.route("/career-coach/history", methods=["GET"])
def career_coach_history():

    if "user_id" not in session:
        return {
            "success": False,
            "error": "Please login first."
        }, 401

    user_id = session["user_id"]

    conversations = (
        CareerConversation.query
        .filter_by(user_id=user_id)
        .order_by(
            CareerConversation.updated_at.desc()
        )
        .all()
    )

    history = []

    for conversation in conversations:

        history.append({
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat()
            if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat()
            if conversation.updated_at else None
        })

    return {
        "success": True,
        "conversations": history
    }
# ==========================================================
# CAREER COACH — LOAD CHAT
# ==========================================================

@app.route("/career-coach/chat/<int:conversation_id>", methods=["GET"])
def load_career_chat(conversation_id):

    if "user_id" not in session:
        return {
            "success": False,
            "error": "Please login first."
        }, 401

    user_id = session["user_id"]

    conversation = (
        CareerConversation.query
        .filter_by(
            id=conversation_id,
            user_id=user_id
        )
        .first()
    )

    if not conversation:
        return {
            "success": False,
            "error": "Conversation not found."
        }, 404

    messages = (
        CareerConversationMessage.query
        .filter_by(
            user_id=user_id,
            conversation_id=conversation_id
        )
        .order_by(
            CareerConversationMessage.created_at.asc()
        )
        .all()
    )

    chat_messages = []

    for record in messages:

        chat_messages.append({
            "role": record.role,
            "message": record.message
        })

    return {
        "success": True,
        "conversation": {
            "id": conversation.id,
            "title": conversation.title
        },
        "messages": chat_messages
    }
# ==========================================================
# AI CAREER COACH PAGE
# ==========================================================

@app.route("/career-coach")
def career_coach_page():

    # ------------------------------------------------------
    # CHECK LOGIN
    # ------------------------------------------------------

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
    # GET STUDENT PROFILE
    # ------------------------------------------------------

    student_profile = (
        StudentProfile.query
        .filter_by(user_id=user_id)
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
    # GET LATEST AI ANALYSIS
    # ------------------------------------------------------

    analysis = (
        AIAnalysis.query
        .filter_by(user_id=user_id)
        .order_by(
            AIAnalysis.created_at.desc()
        )
        .first()
    )

    # ------------------------------------------------------
    # LOAD CAREER ANALYSIS
    # ------------------------------------------------------

    if analysis:

        career_data = safe_json_load(
            analysis.career_recommendations,
            {}
        )

        if isinstance(career_data, dict):

            career_analysis.update(
                career_data
            )

    # ------------------------------------------------------
    # NORMALIZE RECOMMENDED ROLES
    # ------------------------------------------------------

    roles = career_analysis.get(
        "recommended_roles",
        []
    )

    normalized_roles = []

    if isinstance(roles, list):

        for role in roles:

            if isinstance(role, dict):

                normalized_roles.append(role)

            elif isinstance(role, str):

                parsed_role = safe_json_load(
                    role,
                    None
                )

                if isinstance(
                    parsed_role,
                    dict
                ):

                    normalized_roles.append(
                        parsed_role
                    )

                else:

                    try:

                        parsed_role = ast.literal_eval(
                            role
                        )

                        if isinstance(
                            parsed_role,
                            dict
                        ):

                            normalized_roles.append(
                                parsed_role
                            )

                    except (
                        ValueError,
                        SyntaxError
                    ):

                        pass

    career_analysis[
        "recommended_roles"
    ] = normalized_roles

    # ------------------------------------------------------
    # LOAD SKILL GAP
    # ------------------------------------------------------

    if analysis:

        skill_gap_data = safe_json_load(
            analysis.skill_gap,
            {}
        )

        if isinstance(
            skill_gap_data,
            dict
        ):

            skill_gap.update(
                skill_gap_data
        
         )
             # ------------------------------------------------------
    # LOAD CAREER COACH CONVERSATION HISTORY
    # ------------------------------------------------------

    conversation_records = (
        CareerConversationMessage.query
        .filter_by(
            user_id=user_id
        )
        .order_by(
            CareerConversationMessage.created_at.asc()
        )
        .all()
    )

    conversation_history = []

    for record in conversation_records:

        conversation_history.append({
            "role": record.role,
            "message": record.message
        })

    # ------------------------------------------------------
    # DISPLAY CAREER COACH
    # ------------------------------------------------------

    return render_template(
        "career_coach_page.html",

        user=user,

        student_profile=student_profile,

        career_analysis=career_analysis,

        skill_gap=skill_gap,
            
        conversation_history=conversation_history
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
    request_start_time = time.perf_counter()

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

        "name": student_profile.candidate_name or "",

        "email": student_profile.candidate_email or "",

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

    rag_start_time = time.perf_counter()
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
    # ------------------------------------------------------

    conversation_id = data.get("conversation_id")

    # Create a new conversation if one was not provided
    if not conversation_id:

        conversation = CareerConversation(
            user_id=user_id,
            title="New Chat"
        )

        db.session.add(conversation)
        db.session.commit()

        conversation_id = conversation.id

    else:

        conversation = (
            CareerConversation.query
            .filter_by(
                id=conversation_id,
                user_id=user_id
            )
            .first()
        )

        if not conversation:

            return {
                "success": False,
                "error": "Conversation not found."
            }, 404


    conversation_records = (
        CareerConversationMessage.query
        .filter_by(
            user_id=user_id,
            conversation_id=conversation_id
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

    llm_start_time = time.perf_counter()

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

    finally:

        llm_end_time = time.perf_counter()

        llm_time = (
            llm_end_time
            - llm_start_time
        )

        print(
            f"M4.3 LLM PROCESSING TIME: "
            f"{llm_time:.3f} seconds"
        )


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

                conversation_id=conversation_id,

                role="user",

                message=message

            )
        )

        db.session.add(
            user_message_record
        )
        # Set conversation title from the user's first message
             
        if conversation.title == "New Chat":
            clean_title = message.strip()

            if len(clean_title) > 45:
                clean_title = clean_title[:45].rstrip() + "..."

        conversation.title = clean_title

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

                conversation_id=conversation_id,

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

    total_time = (
        time.perf_counter()
        - request_start_time
    )

    print(
        "M3.4 CAREER COACH: Response generated successfully."
    )

    print(
        f"M4.3 TOTAL RESPONSE TIME: "
        f"{total_time:.3f} seconds"
    )

    return {

        "success": True,

        "answer": str(answer),

        "conversation_id": conversation_id

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

        "name": student_profile.candidate_name or "",

        "email": student_profile.candidate_email or "",

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

        "name": student_profile.candidate_name or "",

        "email": student_profile.candidate_email or "",

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

        "name": student_profile.candidate_name or "",

        "email": student_profile.candidate_email or "",

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

# ==========================================================
# MILESTONE 4.1 - APPLICATION TRACKING
# ==========================================================
@app.route("/applications")
def applications_page():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    applications = (
        Application.query
        .filter_by(user_id=user_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    total_applications = len(applications)

    active_statuses = [
        "Saved",
        "Planning to apply",
        "Applied",
        "Application under review",
        "Shortlisted",
        "Interview scheduled",
        "Interview completed"
    ]

    active_applications = sum(
        1 for application in applications
        if application.status in active_statuses
    )

    interviews = sum(
        1 for application in applications
        if application.interview_date is not None
    )

    offers = sum(
        1 for application in applications
        if application.status == "Offer received"
    )

    rejected = sum(
        1 for application in applications
        if application.status == "Rejected"
    )

    # ==========================================================
    # M4.1 - DEADLINE & REMINDER MANAGEMENT
    # ==========================================================

    today = datetime.now()

    # ----------------------------------------------------------
    # Upcoming application deadlines
    # ----------------------------------------------------------

    upcoming_deadlines = [
        application
        for application in applications
        if (
            application.deadline
            and application.deadline >= today
            and application.status not in [
                "Rejected",
                "Withdrawn",
                "Offer received"
            ]
        )
    ]

    # ----------------------------------------------------------
    # Upcoming scheduled interviews
    # ----------------------------------------------------------

    upcoming_interviews = [
        application
        for application in applications
        if (
            application.interview_date
            and application.interview_date >= today
            and application.interview_status
            and application.interview_status.lower() == "scheduled"
        )
    ]

    # ----------------------------------------------------------
    # Pending applications
    # ----------------------------------------------------------

    pending_applications = [
        application
        for application in applications
        if application.status in [
            "Applied",
            "Application under review",
            "Shortlisted"
        ]
    ]

    # ----------------------------------------------------------
    # Follow-up applications
    # ----------------------------------------------------------

    follow_up_applications = [
        application
        for application in applications
        if (
            application.follow_up_date
            and application.follow_up_date >= today
            and application.status not in [
                "Rejected",
                "Withdrawn",
                "Offer received"
            ]
        )
    ]

    # ----------------------------------------------------------
    # Sort reminders by date
    # ----------------------------------------------------------

    upcoming_deadlines.sort(
        key=lambda application: application.deadline
    )

    upcoming_interviews.sort(
        key=lambda application: application.interview_date
    )

    follow_up_applications.sort(
        key=lambda application: application.follow_up_date
    )

    # ==========================================================
    # DISPLAY APPLICATION TRACKING DASHBOARD
    # ==========================================================

    return render_template(
        "applications_page.html",

        applications=applications,

        total_applications=total_applications,

        active_applications=active_applications,

        interviews=interviews,

        offers=offers,

        rejected=rejected,

        upcoming_deadlines=upcoming_deadlines,

        upcoming_interviews=upcoming_interviews,

        pending_applications=pending_applications,

        follow_up_applications=follow_up_applications
    )
# ==========================================================
# MILESTONE 4.1 - ADD APPLICATION
# ==========================================================

@app.route("/applications/add", methods=["GET", "POST"])
def add_application():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        user_id = session["user_id"]
        application_date = request.form.get("application_date")
        deadline = request.form.get("deadline")
        follow_up_date = request.form.get("follow_up_date")     
        interview_date = request.form.get("interview_date")

        application = Application(
            user_id=user_id,
            job_id=request.form.get("job_id") or "manual",
            company=request.form.get("company"),
            job_title=request.form.get("job_title"),
            job_description=request.form.get(
                "job_description"
            ),
            application_date=(
                datetime.strptime(
                    application_date,
                    "%Y-%m-%d"
                )
                if application_date
                else None
            ),
            deadline=(
                datetime.strptime(
                    deadline,
                    "%Y-%m-%d"
                )
                if deadline
                else None
            ),
            follow_up_date=(
            datetime.strptime(
            follow_up_date,
            "%Y-%m-%d"
                )
            if follow_up_date
            else None
            ),
            status=request.form.get(
                "status",
                "Saved"
            ),
            interview_date=(
                datetime.strptime(
                    interview_date,
                    "%Y-%m-%d"
                )
                if interview_date
                else None
            ),
            interview_status=request.form.get(
                "interview_status"
            ),
            notes=request.form.get("notes")
        )

        db.session.add(application)
        db.session.commit()

        return redirect(
            url_for("applications_page")
        )

    return render_template(
        "add_application.html"
    )
    # ==========================================================
# MILESTONE 4.1 - EDIT APPLICATION
# ==========================================================

@app.route("/applications/edit/<int:application_id>", methods=["GET", "POST"])
def edit_application(application_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    application = (
        Application.query
        .filter_by(
            id=application_id,
            user_id=user_id
        )
        .first()
    )

    if application is None:
        return "Application not found", 404

    if request.method == "POST":

        application.company = request.form.get("company")
        application.job_title = request.form.get("job_title")
        application.job_description = request.form.get(
            "job_description"
        )

        application_date = request.form.get(
            "application_date"
        )

        deadline = request.form.get(
            "deadline"
        )
        follow_up_date = request.form.get(
            "follow_up_date"
        )

        interview_date = request.form.get(
            "interview_date"
        )

        application.application_date = (
            datetime.strptime(
                application_date,
                "%Y-%m-%d"
            )
            if application_date
            else None
        )

        application.deadline = (
            datetime.strptime(
                deadline,
                "%Y-%m-%d"
            )
            if deadline
            else None
        )
        application.follow_up_date = (
    datetime.strptime(
        follow_up_date,
        "%Y-%m-%d"
    )
    if follow_up_date
    else None
)

        application.status = request.form.get(
            "status",
            "Saved"
        )

        application.interview_date = (
            datetime.strptime(
                interview_date,
                "%Y-%m-%d"
            )
            if interview_date
            else None
        )

        application.interview_status = request.form.get(
            "interview_status"
        )

        application.notes = request.form.get(
            "notes"
        )

        try:
            db.session.commit()

            return redirect(
                url_for("applications_page")
            )

        except Exception as e:

            db.session.rollback()

            print(
                f"APPLICATION UPDATE ERROR: {e}"
            )

            return (
                f"Error updating application: {str(e)}",
                500
            )

    return render_template(
        "edit_application.html",
        application=application
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