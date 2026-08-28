# M1.1 — Research & Technical Understanding

## 1. Internship Application Workflow

The internship application workflow describes the process through which a student
creates a profile, uploads a resume, finds suitable internship opportunities,
applies for internships, and prepares for interviews.

### Basic Workflow

Student
↓
Create Student Profile
↓
Upload Resume
↓
Resume Parsing
↓
Extract Skills, Education, Experience, Projects and Achievements
↓
Create Structured Candidate Profile
↓
Match Candidate with Internship Opportunities
↓
Skill Gap Analysis
↓
Application / Cover Letter Preparation
↓
Interview Preparation

The first milestone mainly focuses on the candidate understanding part:
resume upload, resume parsing, information extraction, and structured candidate
profile creation.

---

## 2. RAG Architecture

RAG stands for Retrieval-Augmented Generation.

RAG combines information retrieval with a Large Language Model (LLM).

Instead of asking an LLM to generate an answer only from its general knowledge,
the system first retrieves relevant information from a knowledge source and
provides that information to the LLM.

### Basic RAG Flow

User Query
↓
Retriever
↓
Relevant Information
↓
LLM
↓
Generated Answer

For the AI Career Companion project, RAG can later be used to retrieve relevant
information such as internship job descriptions, company information, and
candidate information before generating an answer.

RAG implementation is not the main coding requirement of Milestone 1.
Milestone 1 focuses on understanding the concept and building the foundation
for structured candidate data.

---

## 3. Multi-Agent Design Pattern

A multi-agent system consists of multiple specialized AI agents.
Each agent performs a specific responsibility.

For the AI Career Companion system, the proposed agents are:

1. Resume Agent
   - Processes uploaded resumes.
   - Extracts candidate information.

2. Job-Resume Matching Agent
   - Compares candidate skills with internship requirements.
   - Identifies suitable opportunities.

3. Skill Gap Agent
   - Identifies missing skills required for a target internship.

4. Cover Letter Agent
   - Helps generate personalized cover letters.

5. Interview Agent
   - Helps the student prepare for interviews.

6. Career Assistant
   - Acts as a general career guidance assistant.

In Milestone 1, these agents are mainly defined at the architectural level.
A complete multi-agent implementation is not required yet.

---

## 4. Structured Candidate Data

A structured candidate profile stores extracted resume information in an
organized format.

Example information includes:

- Personal information
- Education
- Skills
- Work experience
- Projects
- Certifications
- Achievements
- Interests

Structured data is important because the application can later use this
information for internship matching, skill-gap analysis, interview preparation,
and personalized career assistance.

---

## 5. Technology Choices

The initial technology stack for the project is:

- Frontend: HTML, CSS
- Backend: Python Flask
- Resume Processing: PyPDF2
- LLM: To be finalized
- Data Storage: To be finalized
- Development Environment: Visual Studio Code
- Version Control: Git and GitHub

The technology choices may be updated as the project progresses through
future milestones.

## Conclusion

Milestone 1 focuses on building the foundation of the AI Career Companion.
The main objective is to understand the candidate, process the resume, extract
important information, and store it as structured candidate data. The
architecture will also provide a foundation for RAG and specialized AI agents
in later milestones.