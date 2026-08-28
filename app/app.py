from flask import Flask, render_template, request
import json
import os
from PyPDF2 import PdfReader

app = Flask(__name__, template_folder="../templates")

# Project root folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data and upload folders
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# JSON file where the structured student profile will be stored
PROFILE_FILE = os.path.join(DATA_DIR, "candidate_profile.json")

# Create folders if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def profile():

    if request.method == "POST":

        # -----------------------------
        # 1. Get student information
        # -----------------------------

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

        # -----------------------------
        # 2. Create student profile
        # -----------------------------

        profile_data = {
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
        }

        # -----------------------------
        # 3. Handle resume upload
        # -----------------------------

        resume = request.files.get("resume")

        resume_filename = ""
        resume_text = ""

        if resume and resume.filename:

            resume_filename = resume.filename

            # Save resume inside uploads folder
            resume_path = os.path.join(UPLOAD_DIR, resume_filename)
            resume.save(resume_path)

            # -----------------------------
            # 4. Extract text from PDF
            # -----------------------------

            try:
                reader = PdfReader(resume_path)

                pages_text = []

                for page in reader.pages:
                    text = page.extract_text()

                    if text:
                        pages_text.append(text)

                resume_text = "\n".join(pages_text)

            except Exception as e:
                resume_text = f"Resume extraction failed: {str(e)}"

        # -----------------------------
        # 5. Add resume information
        # -----------------------------

        profile_data["resume"] = {
            "filename": resume_filename,
            "extracted_text": resume_text
        }

        # -----------------------------
        # 6. Save structured profile
        # -----------------------------

        with open(PROFILE_FILE, "w", encoding="utf-8") as file:
            json.dump(profile_data, file, indent=4, ensure_ascii=False)

        print("\nStudent Profile Created")
        print("-----------------------")
        print(json.dumps(profile_data, indent=4, ensure_ascii=False))

        # -----------------------------
        # 7. Show result page
        # -----------------------------

        return render_template(
            "result.html",
            profile=profile_data
        )

    return render_template("profile.html")


if __name__ == "__main__":
    app.run(debug=True)