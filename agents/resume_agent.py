import json


class ResumeAgent:
    """
    Resume Agent responsible for:
    1. Extracting candidate information
    2. Analyzing resume performance
    """

    def __init__(self, client):
        self.client = client

    def analyze(self, resume_text):
        """
        Analyze the resume and return:
        - Candidate profile
        - Resume performance analysis
        """

        prompt = f"""
You are the Resume Agent in an AI Career Companion system.

Analyze the student's resume and return ONLY valid JSON.

Extract information only from the resume. Do not invent or assume
information.

Return exactly this structure:

{{
    "candidate_profile": {{
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
    }},
    "resume_analysis": {{
        "resume_score": 0,
        "strengths": [],
        "weaknesses": [],
        "improvements": [],
        "recommended_roles": [],
        "skill_gaps": []
    }}
}}

Rules:
- resume_score must be a number from 0 to 100.
- Use only information present in the resume.
- Use empty strings/lists when information is unavailable.
- Keep skills, projects, certifications and achievements as individual items.
- Education should include degree, institution, year and CGPA/percentage when available.
- Experience should include company, role and description when available.
- Recommended roles must match the candidate's actual skills, education and projects.
- Skill gaps should contain useful skills that would strengthen the candidate for those roles.
- Do not claim the candidate is definitely eligible for any job or internship.
- Evaluate clarity, education, technical skills, projects, experience,
  certifications, achievements and completeness.
- Return JSON only.

ume:
{resume_text}
"""

        response = self.client.generate(
        prompt,
        response_mime_type="application/json"
        )

        return json.loads(response.text)