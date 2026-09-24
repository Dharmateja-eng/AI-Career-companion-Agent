import json
import time


class M3MockInterviewAgent:
    """
    Optional Milestone 3 Mock Interview Agent.

    Conducts an interactive mock interview for one
    selected internship/job.

    Flow:
    1. Generate interview question
    2. Evaluate student's answer
    3. Provide feedback
    4. Generate the next question
    """

    def __init__(self, client):
        self.client = client

    def _generate_json(self, prompt, max_retries=3):
        """
        Send a Gemini request with automatic retry handling
        for temporary model availability errors.
        """

        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )

                return json.loads(response.text)

            except Exception as e:
                last_error = e

                error_text = str(e)

                # Retry temporary Gemini availability errors.
                if "503" in error_text or "UNAVAILABLE" in error_text:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt

                        print(
                            f"Gemini temporarily unavailable. "
                            f"Retrying in {wait_time} seconds..."
                        )

                        time.sleep(wait_time)
                        continue

                # For other errors, stop immediately.
                raise

        raise last_error

    def generate_question(
        self,
        candidate_profile,
        job,
        interview_context=None,
        previous_questions=None
    ):
        """
        Generate one interview question based on the
        selected job and student's profile.
        """

        prompt = f"""
You are an AI Mock Interviewer in an AI Career Companion system.

Your task is to conduct an interactive mock interview
for ONE SPECIFIC internship or job.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
INTERVIEW CONTEXT
--------------------------------

{json.dumps(interview_context or {}, indent=4)}

--------------------------------
PREVIOUS QUESTIONS
--------------------------------

{json.dumps(previous_questions or [], indent=4)}

--------------------------------
TASK
--------------------------------

Generate ONE interview question.

The question should be relevant to the selected job
and the student's profile.

Possible question types:

- Technical
- Resume
- Project
- Role-specific
- HR / General

Avoid repeating previous questions.

The question should be suitable for an internship
or entry-level candidate.

--------------------------------
RULES
--------------------------------

1. Do not invent information about the student.

2. Use only information present in the student profile
   when asking resume or project questions.

3. Use only the selected job information when asking
   job-specific questions.

4. Do not assume that the student has a skill that is
   not present in the profile.

5. Do not repeat a previous question.

6. Keep the question clear and understandable.

7. Return ONLY valid JSON.

--------------------------------
OUTPUT FORMAT
--------------------------------

{{
    "question": "",
    "question_type": "",
    "topic": ""
}}
"""

        return self._generate_json(prompt)

    def evaluate_answer(
        self,
        candidate_profile,
        job,
        question,
        answer,
        interview_context=None
    ):
        """
        Evaluate the student's answer to one mock
        interview question.
        """

        prompt = f"""
You are an AI Mock Interview Evaluator in an
AI Career Companion system.

Evaluate the student's answer to ONE interview question.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
INTERVIEW CONTEXT
--------------------------------

{json.dumps(interview_context or {}, indent=4)}

--------------------------------
QUESTION
--------------------------------

{question}

--------------------------------
STUDENT ANSWER
--------------------------------

{answer}

--------------------------------
TASK
--------------------------------

Evaluate the answer based on:

1. Relevance to the question
2. Technical correctness when applicable
3. Understanding
4. Clarity
5. Completeness
6. Communication

Provide:

- A score from 0 to 100
- What the student did well
- What could be improved
- Specific improvement advice
- A better approach for answering the question

--------------------------------
IMPORTANT RULES
--------------------------------

1. Evaluate only the answer provided.

2. Do not invent things the student said.

3. Do not assume knowledge that is not demonstrated
   in the answer.

4. Do not claim that the student will pass or fail
   the actual interview.

5. Feedback should be constructive and practical.

6. If the answer is partially correct, clearly explain
   what is correct and what is missing.

7. Return ONLY valid JSON.

--------------------------------
OUTPUT FORMAT
--------------------------------

{{
    "score": 0,
    "strengths": [],
    "areas_to_improve": [],
    "feedback": "",
    "improvement_advice": "",
    "better_answer_approach": ""
}}
"""

        return self._generate_json(prompt)

    def generate_final_summary(
        self,
        candidate_profile,
        job,
        interview_results
    ):
        """
        Generate a final summary after the mock interview.
        """

        prompt = f"""
You are an AI Mock Interview Summary Agent.

Prepare a final summary of a student's mock interview
for ONE SPECIFIC internship/job.

--------------------------------
STUDENT PROFILE
--------------------------------

{json.dumps(candidate_profile, indent=4)}

--------------------------------
SELECTED JOB
--------------------------------

{json.dumps(job, indent=4)}

--------------------------------
INTERVIEW RESULTS
--------------------------------

{json.dumps(interview_results, indent=4)}

--------------------------------
TASK
--------------------------------

Summarize the mock interview.

Include:

1. Overall performance
2. Strong areas
3. Areas that need improvement
4. Technical topics to revise
5. Communication improvements
6. Practical next steps

Calculate the average score from the provided
interview results.

Do not invent information.

--------------------------------
OUTPUT FORMAT
--------------------------------

{{
    "average_score": 0,
    "overall_performance": "",
    "strong_areas": [],
    "improvement_areas": [],
    "technical_revision_topics": [],
    "communication_advice": [],
    "next_steps": []
}}

Return ONLY valid JSON.
"""

        return self._generate_json(prompt)