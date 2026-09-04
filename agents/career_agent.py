import json


class CareerAgent:
    """
    Career Agent responsible for recommending
    suitable career roles based on the student's
    profile.
    """

    def __init__(self, client):
        self.client = client

    def recommend(self, candidate_profile):
        """
        Analyze the candidate profile and recommend
        suitable career roles.
        """

        prompt = f"""
You are the Career Agent in an AI Career Companion system.

Analyze the following candidate profile carefully.

Candidate Profile:

{json.dumps(candidate_profile, indent=4)}

Your task is to recommend suitable career roles
based ONLY on the candidate's education, skills,
experience, projects, certifications and achievements.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "recommended_roles": [
        {{
            "role": "",
            "reason": "",
            "required_skills": [],
            "candidate_matching_skills": []
        }}
    ]
}}

Rules:

1. Recommend realistic career roles based on the
   candidate's actual profile.

2. Do not invent skills or experience.

3. Do not claim that the candidate is definitely
   eligible for a particular company or internship.

4. Recommend between 3 and 5 suitable roles.

5. Each role must have a clear reason explaining
   why it matches the candidate.

6. required_skills should contain important skills
   normally needed for that role.

7. candidate_matching_skills should contain only
   skills already present in the candidate profile.

8. Keep skills as individual items.

9. Do not recommend a role only because it is popular.
   It must have a reasonable connection to the
   candidate's profile.

10. Return JSON only.
"""

        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)