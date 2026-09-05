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

Analyze the student's resume carefully.

Your tasks are:

1. Extract the candidate's information.
2. Evaluate the overall resume quality.
3. Identify resume strengths.
4. Identify resume weaknesses.
5. Suggest improvements.
6. Recommend suitable career roles.
7. Identify useful skills the candidate should improve.

Return ONLY valid JSON.

Use exactly this structure:

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

1. Give resume_score as a number between 0 and 100.

2. Do not invent information about the candidate.

3. Use ONLY information available in the resume.

4. If information is not available, use an empty
   string or empty list.

5. Keep skills as individual items.

6. Keep projects as individual items.

7. Keep certifications as individual items.

8. Education should contain degree, institution,
   year and CGPA/percentage when available.

9. Experience should contain company, role and
   description when available.

10. Achievements should contain actual achievements
    mentioned in the resume.

11. Languages should contain languages explicitly
    mentioned in the resume.

12. Evaluate the resume based on factors such as:
    - clarity
    - education
    - technical skills
    - projects
    - experience
    - certifications
    - achievements
    - overall completeness

13. Do not give a high score simply because the
    candidate has many skills.

14. If experience is missing, mention it as a
    possible improvement when appropriate.

15. Recommended roles must be based on the
    candidate's actual skills, education and projects.

16. Skill gaps should contain useful skills that
    would help the candidate become stronger for
    the recommended roles.

17. Do not claim that the candidate is definitely
    eligible for a real internship or job.

18. Return JSON only.

Resume:

{resume_text}
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)