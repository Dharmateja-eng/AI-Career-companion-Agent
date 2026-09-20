import json


class M3InterviewAgent:
    """
    Milestone 3.3 Interview Preparation Agent.

    Generates role-specific interview questions,
    preparation guidance, and revision topics using
    the student's profile, selected job, and skill gaps.
    """

    def __init__(self, client):
        self.client = client

    def prepare(self, candidate_profile, job, skill_gap=None):
        """
        Generate interview preparation material for
        one selected internship/job.
        """

        prompt = f"""
You are the Interview Preparation Agent in an AI Career Companion system.

Your task is to prepare a student for an interview for ONE SPECIFIC
internship or job.

Use the student's profile, the selected job, and the available
skill-gap analysis.

Do not generate generic interview preparation that ignores the
selected job.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
SKILL GAP ANALYSIS
--------------------------------

{json.dumps(skill_gap or {}, indent=4)}

--------------------------------
TASK
--------------------------------

Generate a personalized interview preparation plan.

Include the following categories:

1. Technical Questions
   - Questions related to the technical skills required by the job.
   - Focus on technologies and concepts mentioned in the job.

2. Resume Questions
   - Questions that an interviewer could ask based on the student's
     actual profile, education, skills, projects, certifications,
     and experience.

3. Project Questions
   - Questions about projects actually present in the student's profile.
   - Focus on the student's contribution, technologies used,
     implementation, challenges, and learning.

4. Role-Specific Questions
   - Questions related to the responsibilities of the selected job.

5. HR / General Questions
   - Common interview questions relevant to an internship/job applicant.

6. Preparation Guidance
   - Give practical preparation advice for each important question
     or topic.

7. Revision Topics
   - Identify technical concepts the student should revise before
     the interview.
   - Give priority to topics directly connected to the selected job.

8. Skill-Gap Preparation
   - Explain which identified skill gaps should be prepared before
     the interview.

--------------------------------
IMPORTANT RULES
--------------------------------

1. Do not invent information about the student.

2. Use only information present in the student profile when creating
   resume and project questions.

3. Do not invent projects, certifications, education, experience,
   achievements, or technologies for the student.

4. Use only the selected job information when describing job
   requirements and responsibilities.

5. Questions should be specific to the selected job whenever possible.

6. Do not claim that the student is guaranteed to pass or get the job.

7. Preparation guidance should be practical and actionable.

8. Keep questions as separate items.

9. Keep preparation guidance as separate items.

10. Keep revision topics as separate items.

11. If information is missing, do not guess.

12. Return ONLY valid JSON.

--------------------------------
OUTPUT FORMAT
--------------------------------

{{
    "job_id": "",
    "job_title": "",

    "technical_questions": [],

    "resume_questions": [],

    "project_questions": [],

    "role_specific_questions": [],

    "hr_questions": [],

    "preparation_guidance": [],

    "revision_topics": [],

    "skill_gap_preparation": []
}}

--------------------------------
QUESTION QUALITY RULES
--------------------------------

Technical questions should test understanding,
not just ask the student to define a technology.

Resume questions should be based on actual information
from the student's profile.

Project questions should focus on projects actually
mentioned in the student's profile.

Role-specific questions should reflect the selected
job's responsibilities.

HR questions should be suitable for an internship or
entry-level candidate.

Preparation guidance should explain what the student
should study or practice.

Revision topics should prioritize skills and concepts
that are relevant to the selected job.

Return JSON only.
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)