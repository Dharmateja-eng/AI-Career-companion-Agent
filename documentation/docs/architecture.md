# M1.2 — System Architecture

## 1. System Overview

The AI Career Companion is designed to help students manage their internship
preparation and career-related activities.

The first milestone focuses on building the foundation of the system.

The main pipeline is:

Student
→ Resume Upload
→ Resume Parsing
→ LLM-based Information Extraction
→ Structured Candidate Profile
→ Storage

Future milestones will use the structured candidate profile for internship
matching, skill-gap analysis, cover letter generation, interview preparation,
and career assistance.

---

## 2. Main System Components

### 2.1 Student/User Interface

The frontend provides an interface for the student to:

- Create a student profile
- Upload a resume
- View extracted profile information

Technology:
- HTML
- CSS

### 2.2 Backend/API Layer

The backend handles communication between the frontend and other system
components.

Responsibilities:

- Receive resume uploads
- Validate uploaded files
- Store resume files
- Send resumes to the parsing module
- Send extracted text to the LLM
- Store the structured candidate profile

Technology:
- Python
- Flask

### 2.3 Resume Upload and Storage

This component receives the student's resume and stores the uploaded file.

The uploaded resume can be stored temporarily in the uploads directory during
Milestone 1.

### 2.4 Resume Parsing Module

The resume parser extracts text from uploaded PDF resumes.

Technology:
- PyPDF2

The extracted text is then passed to the LLM for structured information
extraction.

### 2.5 LLM Extraction Module

The LLM processes the extracted resume text and converts unstructured resume
information into structured candidate information.

The LLM can extract:

- Personal information
- Education
- Skills
- Experience
- Projects
- Certifications
- Achievements
- Interests

The exact LLM provider will be finalized during implementation.

### 2.6 Candidate Profile Storage

The extracted information is stored as a structured candidate profile.

This structured information will later support:

- Internship matching
- Skill-gap analysis
- Cover letter generation
- Interview preparation
- Career assistance

### 2.7 AI Agent Layer

The system is designed with specialized agents.

The proposed agents are:

1. Resume Agent
2. Job-Resume Matching Agent
3. Skill Gap Agent
4. Cover Letter Agent
5. Interview Agent
6. Career Assistant

During Milestone 1, these agents are primarily defined at the architectural
level.

### 2.8 RAG Pipeline

RAG stands for Retrieval-Augmented Generation.

In future milestones, the RAG pipeline can retrieve relevant information from
sources such as internship job descriptions and provide that information to
the LLM before generating responses.

Complete RAG implementation is not required for the foundation of Milestone 1.

---

## 3. Data Flow

The main Milestone 1 data flow is:

Student
↓
Web Interface
↓
Resume Upload
↓
Flask Backend
↓
Resume Storage
↓
Resume Parser
↓
Extracted Resume Text
↓
LLM
↓
Structured Candidate Profile
↓
Candidate Profile Storage

---

## 4. Future Data Flow

In future milestones:

Candidate Profile
+
Internship Job Description
↓
RAG / Retrieval
↓
Relevant Information
↓
AI Agents
↓
Personalized Career Response

---

## 5. Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS |
| Backend | Python Flask |
| Resume Parsing | PyPDF2 |
| LLM | To be finalized |
| Data Storage | To be finalized |
| Development Environment | Visual Studio Code |
| Version Control | Git |
| Repository | GitHub |

---

## 6. Milestone 1 Scope

Milestone 1 focuses on creating the foundation of the AI Career Companion.

The working pipeline should demonstrate:

1. Student uploads a resume.
2. The system reads the resume.
3. Resume text is extracted.
4. The extracted information is processed using an LLM.
5. Skills, education, experience, projects and other relevant information are
   converted into structured data.
6. The structured candidate profile is stored.

RAG and complete multi-agent functionality will be developed in later
milestones.