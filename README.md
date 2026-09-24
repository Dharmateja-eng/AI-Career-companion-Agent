# AI Career Companion Agent

An AI-powered career assistance platform that analyzes student resumes, builds structured candidate profiles, identifies skill gaps, provides career recommendations, prepares students for interviews, and matches candidates with relevant job opportunities using Retrieval-Augmented Generation (RAG).

## Project Overview

The AI Career Companion Agent is designed to support students throughout their career preparation journey.

The system uses multiple AI agents and a RAG-based job matching pipeline to understand a candidate's resume, retrieve relevant job postings, compare candidate skills with job requirements, and provide compatibility scores and explanations.

## Key Features

- Resume upload and PDF text extraction
- AI-powered resume analysis
- Structured candidate profile generation
- Career role recommendations
- Skill gap analysis
- AI-generated interview preparation
- Internship/job knowledge base
- Semantic job retrieval using RAG
- Job-Resume Matching Agent
- Compatibility scoring
- Matching and missing skill identification
- AI-generated matching explanations
- Integrated career dashboard
- Evaluation using multiple sample student profiles

---

# Milestone 1 - Candidate Understanding

Milestone 1 focused on understanding the candidate from their resume and building the initial AI career assistance pipeline.

### Implemented Features

- Resume PDF upload
- Resume text extraction using PyPDF2
- Candidate information extraction using Gemini
- Structured candidate profile generation
- Resume analysis and scoring
- Career recommendations
- Skill gap analysis
- Interview preparation
- Multiple AI career agents
- End-to-end resume processing
- Candidate profile storage in JSON

### Milestone 1 Agents

1. Resume Agent
2. Career Agent
3. Skill Gap Agent
4. Interview Agent

### Milestone 1 Workflow

```text
Student
   ↓
Resume Upload
   ↓
Flask Backend
   ↓
PDF Text Extraction
   ↓
Gemini LLM
   ↓
Structured Candidate Profile
   ↓
Career / Skill Gap / Interview Agents
   ↓
Career Dashboard
---

# Milestone 2 - RAG-Based Job Matching

Milestone 2 extends the system with an internship/job knowledge base and a RAG-based semantic job matching pipeline.

## 1. Job Knowledge Base

A curated dataset of **200 technical job postings** was prepared from a sample job-posting dataset.

The dataset was cleaned, filtered, deduplicated, and organized into eight technical categories:

- Software Development
- Web Development
- Data / AI
- Mobile Development
- Database / SQL
- Cloud / DevOps
- Testing
- Analytics

The final knowledge base contains:

- 200 job postings
- Standardized job information
- Cleaned and searchable job descriptions
- No missing values after preprocessing

> Note: The dataset contains historical/sample job postings and is used as a knowledge base for demonstrating semantic job matching. It does not represent live job vacancies.

## 2. RAG Pipeline

The job postings are processed through a Retrieval-Augmented Generation (RAG) pipeline.

### RAG Workflow

```text
Job Postings
     ↓
Data Cleaning
     ↓
Job Chunking
     ↓
Text Embeddings
     ↓
FAISS Vector Index
     ↓
Semantic Retrieval
     ↓
Relevant Job Postings

---

# Milestone 3 - AI Career Assistance Agents

Milestone 3 extends the AI Career Companion Agent with specialized agents that provide personalized career guidance, skill-gap analysis, resume and cover letter customization, interview preparation, and conversational career assistance.

## 1. M3.1 - Skill Gap Analysis Agent

The Skill Gap Analysis Agent compares the student's candidate profile with the requirements of a selected job role.

### Key Functions

- Compares candidate skills with job requirements
- Identifies missing skills
- Identifies partially matched skills
- Identifies existing/strong skills
- Provides recommendations for improving skill gaps
- Explains why a skill is important for the selected role

### Workflow

```text
Student Profile
       ↓
Selected Job Requirements
       ↓
Skill Comparison
       ↓
Skill Gap Identification
       ↓
Missing / Partial / Existing Skills
       ↓
Personalized Improvement Recommendations