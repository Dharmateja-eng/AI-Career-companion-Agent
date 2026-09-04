import os
import json

from flask import Flask, render_template, request
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from google import genai

from agents.resume_agent import ResumeAgent
from agents.career_agent import CareerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.interview_agent import InterviewAgent


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file")


# --------------------------------------------------
# Flask configuration
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

PROFILE_FILE = os.path.join(
    DATA_DIR,
    "candidate_profile.json"
)


# --------------------------------------------------
# Create required directories
# --------------------------------------------------

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --------------------------------------------------
# Create Flask application
# --------------------------------------------------

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# --------------------------------------------------
# AI Agents
# --------------------------------------------------

resume_agent = ResumeAgent(client)

career_agent = CareerAgent(client)

skill_gap_agent = SkillGapAgent(client)

interview_agent = InterviewAgent(client)


# --------------------------------------------------
# Resume text extraction
# --------------------------------------------------

def extract_resume_text(pdf_path):

    text = ""

    reader = PdfReader(pdf_path)

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text.strip()


# --------------------------------------------------
# Home / Resume Upload
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def profile():

    # --------------------------------------------------
    # Display upload page
    # --------------------------------------------------

    if request.method == "GET":

        return render_template(
            "profile.html"
        )


    # --------------------------------------------------
    # Get uploaded resume
    # --------------------------------------------------

    resume = request.files.get("resume")


    if not resume or resume.filename == "":

        return "Please upload a resume PDF."


    # --------------------------------------------------
    # Check PDF
    # --------------------------------------------------

    if not resume.filename.lower().endswith(".pdf"):

        return "Please upload a PDF resume."


    # --------------------------------------------------
    # Secure uploaded filename
    # --------------------------------------------------

    filename = secure_filename(
        resume.filename
    )


    if not filename:

        return "Invalid resume filename."


    # --------------------------------------------------
    # Save resume
    # --------------------------------------------------

    resume_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    resume.save(resume_path)


    # --------------------------------------------------
    # Extract resume text
    # --------------------------------------------------

    try:

        resume_text = extract_resume_text(
            resume_path
        )

    except Exception as e:

        return f"Error reading resume: {str(e)}"


    if not resume_text:

        return "Could not extract text from the resume."


    # --------------------------------------------------
    # RESUME AGENT
    # --------------------------------------------------

    try:

        resume_result = resume_agent.analyze(
            resume_text
        )

    except Exception as e:

        return f"Resume Agent Error: {str(e)}"


    # --------------------------------------------------
    # Get candidate profile
    # --------------------------------------------------

    candidate_profile = resume_result.get(
        "candidate_profile",
        {}
    )


    # --------------------------------------------------
    # Get resume analysis
    # --------------------------------------------------

    resume_analysis = resume_result.get(
        "resume_analysis",
        {}
    )


    # --------------------------------------------------
    # CAREER AGENT
    # --------------------------------------------------

    try:

        career_result = career_agent.recommend(
            candidate_profile
        )

    except Exception as e:

        return f"Career Agent Error: {str(e)}"


    # --------------------------------------------------
    # Get recommended roles
    # --------------------------------------------------

    recommended_roles = career_result.get(
        "recommended_roles",
        []
    )


    # --------------------------------------------------
    # Determine target role
    # --------------------------------------------------

    target_role = ""

    if recommended_roles:

        target_role = recommended_roles[0].get(
            "role",
            ""
        )


    # --------------------------------------------------
    # SKILL GAP AGENT
    # --------------------------------------------------

    skill_gap_result = {}


    if target_role:

        try:

            skill_gap_result = skill_gap_agent.analyze(
                candidate_profile,
                target_role
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


    # --------------------------------------------------
    # INTERVIEW AGENT
    # --------------------------------------------------

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


    # --------------------------------------------------
    # Complete Candidate Profile
    # --------------------------------------------------

    profile_data = {

        # --------------------------------------------------
        # Student Profile
        # --------------------------------------------------

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


        # --------------------------------------------------
        # Resume
        # --------------------------------------------------

        "resume": {

            "filename": filename,

            "extracted_text": resume_text,

            "llm_extracted_profile": candidate_profile
        },


        # --------------------------------------------------
        # Resume Agent Output
        # --------------------------------------------------

        "resume_analysis": resume_analysis,


        # --------------------------------------------------
        # Career Agent Output
        # --------------------------------------------------

        "career_analysis": {

            "recommended_roles": recommended_roles
        },


        # --------------------------------------------------
        # Skill Gap Agent Output
        # --------------------------------------------------

        "skill_gap_analysis": skill_gap_result,


        # --------------------------------------------------
        # Interview Agent Output
        # --------------------------------------------------

        "interview_analysis": interview_result
    }


    # --------------------------------------------------
    # Save candidate profile
    # --------------------------------------------------

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

        return f"Error saving profile: {str(e)}"


    # --------------------------------------------------
    # Display Dashboard
    # --------------------------------------------------

    return render_template(
        "dashboard.html",
        profile=profile_data
    )


# --------------------------------------------------
# Run Flask application
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )