import json
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()


class JobMatchingAgent:

    def __init__(self):
        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

    def match_jobs(self, candidate_profile, jobs):

        prompt = f"""
You are a Job-Resume Matching Agent.

Compare the student's profile with the retrieved job postings.

Student Profile:
{json.dumps(candidate_profile, indent=2)}

Retrieved Jobs:
{json.dumps(jobs, indent=2)}

For each job, evaluate:

1. Skill match
2. Education match
3. Experience match
4. Overall compatibility
5. Reason for the score

Give a compatibility score from 0 to 100.

Return ONLY valid JSON in this format:

{{
    "matched_jobs": [
        {{
            "jobid": "",
            "job_title": "",
            "company": "",
            "compatibility_score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "reasoning": ""
        }}
    ]
}}

Rules:
- Do not invent candidate skills.
- Do not invent job requirements.
- Base the score only on the provided information.
- Higher score means better compatibility.
- Return the jobs in descending order of compatibility score.
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

        result = response.text.strip()

        # Remove markdown code fences if Gemini adds them
        if result.startswith("```"):
            result = result.replace("```json", "")
            result = result.replace("```", "")
            result = result.strip()

        return json.loads(result)