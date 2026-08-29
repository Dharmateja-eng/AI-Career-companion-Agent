# AI Career Companion Agent

## Project Overview

AI Career Companion Agent is an AI-based system designed to help students with the internship application process and interview preparation.

The system focuses on understanding a student's profile from their resume and storing the extracted information in a structured format.

The structured candidate profile can later be used for:

- Internship matching
- Skill gap analysis
- Resume improvement
- Cover letter generation
- Interview preparation
- Career assistance

---

## Milestone 1

Milestone 1 focuses on the **Foundation & Candidate Understanding** of the AI Career Companion Agent.

### Milestone 1 Objectives

1. Study internship application workflows.
2. Understand RAG architecture.
3. Study multi-agent design patterns.
4. Design the system architecture.
5. Define agent responsibilities.
6. Design the candidate profile data model.
7. Build student profile creation.
8. Implement resume upload.
9. Parse resume PDF files.
10. Extract structured candidate information using an LLM.
11. Store the structured candidate profile.
12. Test resume extraction using multiple sample resumes.

---

## Implemented Features

### Student Profile Module

- Student personal information collection
- Educational information collection
- Technical skills collection
- Experience collection
- Project information collection
- Certification information collection
- Achievement information collection

### Resume Processing

- PDF resume upload
- Resume text extraction using PyPDF2
- LLM-based resume information extraction
- Structured candidate profile generation
- JSON-based candidate profile storage

### Extracted Resume Information

The system extracts:

- Name
- Email
- Phone
- Education
- Skills
- Experience
- Projects
- Certifications
- Achievements
- Languages

---

## System Workflow

```text
Student
   |
   v
Student Profile Form
   |
   v
Resume Upload
   |
   v
PDF Resume
   |
   v
PyPDF2 Resume Text Extraction
   |
   v
Gemini LLM
   |
   v
Structured Candidate Information
   |
   v
Candidate Profile JSON
   |
   v
Profile Result Display