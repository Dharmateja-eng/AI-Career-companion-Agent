import json


class M3ResumeCoverLetterAgent:
    """
    Milestone 3.2 Resume and Cover Letter Customization Agent.

    Creates role-specific resume improvements and a
    tailored cover letter using a student's profile
    and one selected job.
    """

    def __init__(self, client):
        self.client = client

    def customize(self, candidate_profile, job):
        """
        Customize the student's resume and generate
        a role-specific cover letter.
        """

        prompt = f"""
You are the Resume and Cover Letter Customization Agent
in an AI Career Companion system.

Your task is to customize a student's existing profile/resume
for ONE SPECIFIC internship or job posting.

Do not create a completely fictional resume.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
TASK
--------------------------------

Create a tailored application package for this specific job.

Analyze the student's profile and the selected job.

For the RESUME customization:

1. Identify the skills already present in the student profile
   that are most relevant to this job.

2. Identify relevant projects from the student profile.

3. Identify relevant education, certifications, and experience.

4. Suggest which resume sections or items should be
   prioritized for this particular job.

5. Improve existing project or experience bullet points
   so that they are clearer and more relevant to the job.

6. Suggest important keywords from the job that are relevant
   to the student's existing background.

7. Do not add unsupported skills.

8. Do not invent projects.

9. Do not invent work experience.

10. Do not invent certifications.

11. Do not invent achievements, numbers, responsibilities,
    technologies, or results.

For the COVER LETTER:

1. Write a professional role-specific cover letter.

2. Connect the student's actual background and projects
   with the requirements of the selected job.

3. Mention only information supported by the student profile.

4. Explain why the student's existing background is relevant
   to the role.

5. Do not claim experience that is not present.

6. Do not claim that the student has skills that are absent
   from the profile.

7. Keep the letter personalized and professional.

--------------------------------
OUTPUT FORMAT
--------------------------------

Return ONLY valid JSON.

Use exactly this structure:

{{
    "job_id": "",
    "job_title": "",

    "relevant_skills": [],

    "relevant_projects": [],

    "relevant_experience": [],

    "relevant_certifications": [],

    "priority_sections": [],

    "improved_bullet_points": [],

    "recommended_keywords": [],

    "tailored_resume_summary": "",

    "cover_letter": "",

    "review_notes": []
}}

--------------------------------
IMPORTANT RULES
--------------------------------

1. Never invent information about the student.

2. Never invent job requirements.

3. Use only the supplied student profile.

4. Use only the supplied selected job.

5. Preserve factual accuracy.

6. Every improved bullet point must be based on
   an existing project or experience.

7. Recommended keywords should come from the selected
   job and be relevant to the student's actual profile.

8. If information is missing, do not guess.

9. Return JSON only.
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)