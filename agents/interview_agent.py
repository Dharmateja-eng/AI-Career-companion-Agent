import json


class InterviewAgent:
    """
    Interview Agent responsible for generating
    personalized interview preparation based on
    the candidate profile, target role and skill gaps.
    """

    def __init__(self, client):
        self.client = client

    def generate_interview(self, candidate_profile, target_role, skill_gap):

        prompt = f"""
You are the Interview Agent in an AI Career Companion system.

Your task is to create personalized interview preparation
for a student based on their actual candidate profile,
target career role and identified skill gaps.

Candidate Profile:
{json.dumps(candidate_profile, indent=4)}

Target Career Role:
{target_role}

Skill Gap Analysis:
{json.dumps(skill_gap, indent=4)}

Generate interview preparation that is relevant to this
specific candidate and target role.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "target_role": "",
    "technical_questions": [
        {{
            "question": "",
            "difficulty": "",
            "topic": ""
        }}
    ],
    "conceptual_questions": [
        {{
            "question": "",
            "difficulty": "",
            "topic": ""
        }}
    ],
    "hr_questions": [
        {{
            "question": "",
            "purpose": ""
        }}
    ],
    "preparation_tips": []
}}

Rules:

1. Base the questions on the candidate's actual skills,
   projects, education and experience.

2. Do not invent projects, skills or experience.

3. Technical questions should match the target role.

4. Include questions related to the candidate's
   identified skill gaps where appropriate.

5. Generate 5 technical questions.

6. Generate 3 conceptual questions.

7. Generate 3 HR/behavioral questions.

8. Difficulty must be one of:
   "Easy", "Medium", or "Hard".

9. Keep questions realistic for a student or fresher.

10. preparation_tips should contain practical
    preparation suggestions.

11. Return JSON only.
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)