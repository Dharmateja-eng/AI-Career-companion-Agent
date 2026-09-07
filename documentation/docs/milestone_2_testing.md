# Milestone 2 - Retrieval and Job Matching Testing

## 1. Objective

The objective of this testing is to validate the job retrieval and Job-Resume Matching pipeline implemented in Milestone 2.

The system was tested with multiple student resumes to verify whether it can retrieve relevant job postings and generate meaningful compatibility scores based on the candidate profile.

---

## 2. Test Environment

* Job knowledge base: 200 curated job postings
* Job chunks: 535
* Embedding model: Gemini `gemini-embedding-001`
* Embedding dimension: 768
* Vector index: FAISS
* Job Retrieval Agent: Implemented
* Job Matching Agent: Implemented
* Matching model: Gemini `gemini-3.1-flash-lite`

---

## 3. Test Cases

### Test Case 1 - Python Developer Resume

**Input:** Python Developer sample resume

**Expected Result:**

* Retrieve software development, Python, web development or related jobs.
* Matching should consider Python, backend/web technologies and other candidate skills.
* Compatibility scores should reflect the candidate's skills against each retrieved job.

**Observed Result:**

* Relevant software/web development jobs were retrieved.
* Compatibility scores were generated.
* Matching and missing skills were displayed.
* AI reasoning was generated for each matched job.

**Result:** PASS

---

### Test Case 2 - Data Analyst Resume

**Input:** Data Analyst sample resume

**Expected Result:**

* Retrieve data, analytics, SQL or related jobs.
* Jobs should be semantically related to the candidate's profile.
* Compatibility scores should be generated based on the available candidate and job information.

**Observed Result:**

* Relevant data/analytics-related jobs were retrieved.
* Compatibility scores were generated.
* Matching and missing skills were displayed.
* AI reasoning was generated.

**Result:** PASS

---

### Test Case 3 - Additional Student Resume

**Input:** Third sample student resume

**Expected Result:**

* Retrieve jobs related to the candidate's education, skills, projects and experience.
* The system should provide different recommendations based on the candidate profile.

**Observed Result:**

* Relevant jobs were retrieved from the knowledge base.
* Compatibility scores were generated.
* Matching and missing skills were displayed.
* AI reasoning was provided.
* Results changed according to the candidate profile.

**Result:** PASS

---

## 4. Retrieval Quality Validation

The Job Retrieval Agent converts the candidate profile into an embedding and searches the FAISS vector index using semantic similarity.

The system retrieves relevant job chunks and maps them back to unique job postings.

Testing confirmed that the retrieved jobs were generally related to the candidate's skills and profile.

---

## 5. Job Matching Validation

The retrieved jobs are passed to the Job Matching Agent.

For each job, the agent evaluates:

1. Skill match
2. Education match
3. Experience match
4. Overall compatibility
5. Reasoning for the compatibility score

The agent produces:

* Compatibility score
* Matching skills
* Missing skills
* Reasoning

Testing with multiple resumes confirmed that the matching results change according to the candidate profile.

---

## 6. End-to-End Validation

The complete Milestone 2 pipeline was successfully tested:

```text
Student Resume
      ↓
Resume Parsing
      ↓
Candidate Profile
      ↓
Profile Embedding
      ↓
FAISS Semantic Search
      ↓
Relevant Job Retrieval
      ↓
Job Matching Agent
      ↓
Compatibility Score
      ↓
Matching Skills
      ↓
Missing Skills
      ↓
AI Reasoning
      ↓
Dashboard
```

**Overall Result: PASS**

---

## 7. Conclusion

The Milestone 2 retrieval and job matching pipeline was successfully implemented and integrated with the Milestone 1 resume analysis system.

Testing with multiple student resumes demonstrated that the system can retrieve semantically relevant job postings and evaluate their compatibility with the candidate profile.

The results are displayed in the AI Career Companion dashboard for the user.
