from flask import Flask, render_template, request
import json
import os
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="../templates")

# Project root folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data and upload folders
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

PROFILE_FILE = os.path.join(DATA_DIR, "candidate_profile.json")

# Create folders if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Gemini client
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)


def extract_resume_text(pdf_path):
    """Extract text from the uploaded PDF resume."""

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def extract_structured_profile(resume_text):
    """Use Gemini to extract structured information from resume text."""

    prompt = f"""
You are a resume information extraction system.

Analyze the following resume text and extract the candidate's information.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "name": "",
    "email": "",
    "phone": "",
    "education": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "achievements": [],
    "languages": []
}}

Rules:

1. Do not invent information.
2. If information is not available, use an empty string or empty list.
3. Keep skills as individual items.
4. Keep projects as individual items.
5. Keep certifications as individual items.
6. Education should contain degree, institution, year and CGPA/percentage when available.
7. Experience should contain company, role and description when available.
8. Return JSON only.

Resume text:

{resume_text}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)


@app.route("/", methods=["GET", "POST"])
def profile():

    if request.method == "POST":

        # Get student form information
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        degree = request.form.get("degree", "")
        college = request.form.get("college", "")
        graduation_year = request.form.get("graduation_year", "")
        skills = request.form.get("skills", "")
        experience = request.form.get("experience", "")
        projects = request.form.get("projects", "")
        certifications = request.form.get("certifications", "")
        achievements = request.form.get("achievements", "")

        # Get uploaded resume
        resume = request.files.get("resume")

        if not resume or resume.filename == "":
            return "Please upload a resume PDF."

        # Save resume
        resume_path = os.path.join(UPLOAD_DIR, resume.filename)
        resume.save(resume_path)

        # Extract text from PDF
        resume_text = extract_resume_text(resume_path)

        if not resume_text.strip():
            return "Could not extract text from the uploaded PDF."

        # Send resume text to Gemini
        structured_resume = extract_structured_profile(resume_text)

        # Combine form data and resume information
        profile_data = {
            "student_profile": {
                "name": name,
                "email": email,
                "phone": phone,
                "degree": degree,
                "college": college,
                "graduation_year": graduation_year,
                "skills": skills,
                "experience": experience,
                "projects": projects,
                "certifications": certifications,
                "achievements": achievements
            },

            "resume": {
                "filename": resume.filename,
                "extracted_text": resume_text,
                "llm_extracted_profile": structured_resume
            }
        }

        # Save complete profile to JSON
        with open(PROFILE_FILE, "w", encoding="utf-8") as file:
            json.dump(
                profile_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        # Print result in terminal
        print("\nStudent Profile Created")
        print("-----------------------")
        print(json.dumps(
            profile_data,
            indent=4,
            ensure_ascii=False
        ))

        # Send LLM extracted profile to result page
        return render_template(
            "result.html",
            profile=structured_resume,
            resume={
                "filename": resume.filename
            }
        )

    return render_template("profile.html")


if __name__ == "__main__":
    app.run(debug=True)