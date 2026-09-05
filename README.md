# AI Career Companion Agent

An AI-powered career assistance system designed to help students with **resume analysis, career recommendations, skill-gap identification, interview preparation, and internship matching**.

## 🚀 Features

* 📄 Resume upload and PDF text extraction
* 🤖 AI-based candidate profile extraction
* 🎯 Career role recommendations
* 📊 Skill-gap analysis
* 💬 Interview question generation
* 🔎 Semantic job retrieval using RAG
* 🎯 Job-resume compatibility scoring
* 📋 Matching and missing skill analysis

## 📌 Milestones

### Milestone 1 — Candidate Understanding

* Resume parsing and structured profile generation
* Resume analysis and scoring
* Career recommendations
* Skill-gap analysis
* Interview preparation
* Initial multi-agent architecture

### Milestone 2 — Internship Matching

* Curated knowledge base of **200 job postings**
* Job preprocessing and chunking
* Gemini-based embeddings
* FAISS semantic search
* Job Retrieval Agent
* Job Matching Agent
* Compatibility scoring and reasoning
* Validation using multiple sample resumes

## 🏗️ System Workflow

```text
Resume Upload
      ↓
Resume Parsing
      ↓
Candidate Profile
      ↓
AI Career Agents
      ↓
Job Retrieval (RAG)
      ↓
Job Matching
      ↓
Recommendations
```

## 🛠️ Tech Stack

* **Python**
* **Flask**
* **Google Gemini**
* **Gemini Embeddings**
* **FAISS**
* **PyPDF2**
* **Pandas / NumPy**
* **HTML / CSS / JavaScript**
* **Git & GitHub**

## 📂 Project Structure

```text
AI-Career-companion-Agent/
├── agents/
├── app/
├── data/
├── docs/
├── scripts/
├── static/
├── templates/
├── requirements.txt
└── README.md
```

## ▶️ Run Locally

```bash
git clone https://github.com/Dharmateja-eng/AI-Career-companion-Agent.git
cd AI-Career-companion-Agent

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```text
GEMINI_API_KEY=your_api_key_here
```

Run the application:

```bash
python -m app.app
```

## 📈 Project Status

**Milestone 1: Completed ✅**
**Milestone 2: Completed ✅**

More career-assistance features will be added in upcoming milestones.
