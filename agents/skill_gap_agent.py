import json


class SkillGapAgent:
    """
    Skill Gap Agent responsible for comparing
    a student's current skills with the skills
    required for a target career role.
    """

    def __init__(self, client):
        self.client = client

    def analyze(self, candidate_profile, target_role):
        """
        Analyze the candidate's skills and identify
        missing or weak skills for the target role.
        """

        prompt = f"""
You are the Skill Gap Agent in an AI Career Companion system.

Analyze the candidate's current skills and compare
them with the skills commonly required for the
target career role.

Candidate Profile:

{json.dumps(candidate_profile, indent=4)}

Target Career Role:

{target_role}

Return ONLY valid JSON.

Use exactly this structure:

{{
    "target_role": "",
    "current_skills": [],
    "required_skills": [],
    "matching_skills": [],
    "missing_skills": [],
    "skills_to_improve": [],
    "recommendations": []
}}

Rules:

1. Do not invent information about the candidate.

2. current_skills must contain only skills found
   in the candidate profile.

3. Identify relevant skills normally required for
   the target role.

4. matching_skills should contain skills the
   candidate already has that are relevant to
   the target role.

5. missing_skills should contain useful skills
   required for the role that are not present
   in the candidate profile.

6. skills_to_improve should contain skills that
   the candidate already has but could strengthen.

7. recommendations should provide practical ways
   to improve the identified skill gaps.

8. Keep each skill as a separate item.

9. Keep recommendations as separate items.

10. Do not claim that the candidate is eligible
    for a specific company or internship.

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