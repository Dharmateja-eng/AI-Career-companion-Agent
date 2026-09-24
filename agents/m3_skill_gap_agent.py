import json


class M3SkillGapAgent:
    """
    Milestone 3.1 Skill Gap Analysis Agent.

    Compares a student's profile against a
    specific selected job/internship.
    """

    def __init__(self, client):
        self.client = client

    def analyze(self, candidate_profile, job):
        """
        Compare the candidate profile with the
        requirements of a selected job.
        """

        prompt = f"""
You are the Skill Gap Analysis Agent in an AI Career Companion system.

Your task is to compare a student's structured profile
against ONE SPECIFIC internship/job posting.

Do not compare the student with a generic career role.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB / INTERNSHIP
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
TASK
--------------------------------

Analyze the gap between the student's profile and
the selected job requirements.

Consider:

1. Technical skills
2. Soft skills
3. Education
4. Experience
5. Projects
6. Certifications
7. Tools and technologies
8. Required skills
9. Preferred skills
10. Qualifications
11. Experience requirements
12. Education requirements
13. Job responsibilities

Classify the gaps into:

- Critical or missing skills
- Partially demonstrated skills
- Preferred skills
- Experience gaps
- Qualification gaps

Also provide practical personalized recommendations.

For every important gap, explain why that skill,
qualification, or experience matters for this
specific job.

--------------------------------
IMPORTANT RULES
--------------------------------

1. Do not invent information about the student.

2. Use only information actually present in the
   student profile when describing the student's
   current skills, education, experience, projects,
   or certifications.

3. Use only the selected job information provided
   above when describing job requirements.

4. Do not assume that the student has a skill just
   because it is related to another skill.

5. Do not claim that the student is eligible for
   the job.

6. Do not invent company requirements.

7. Distinguish clearly between:
   - skills the student already has
   - skills partially demonstrated
   - skills missing from the profile

8. Recommendations must be practical and personalized.

9. Keep every skill or gap as a separate item.

10. Return ONLY valid JSON.

--------------------------------
OUTPUT FORMAT
--------------------------------

{{
    "job_id": "",
    "job_title": "",
    "critical_missing_skills": [],
    "partially_demonstrated_skills": [],
    "preferred_skills": [],
    "experience_gaps": [],
    "qualification_gaps": [],
    "gap_explanations": [],
    "recommendations": []
}}
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)