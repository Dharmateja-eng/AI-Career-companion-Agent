# Resume Extraction Testing

## Objective

To test the resume parsing and LLM-based structured information extraction functionality of the AI Career Companion Agent.

## Extraction Workflow

Resume PDF
→ PDF Text Extraction using PyPDF2
→ Extracted Resume Text
→ Gemini LLM
→ Structured Candidate Profile
→ JSON Storage

## Test Case 1

### Input
Resume PDF uploaded through the Student Profile form.

### Results

- Resume upload: Successful
- PDF text extraction: Successful
- Name extraction: Successful
- Email extraction: Successful
- Phone extraction: Successful
- Education extraction: Successful
- Skills extraction: Successful
- Experience extraction: Successful
- Projects extraction: Successful
- Certifications extraction: Successful
- Achievements extraction: Successful
- Languages extraction: Successful
- Structured JSON generation: Successful
- Candidate profile JSON storage: Successful

### Status

PASS

---

## Test Case 2

### Input
The same resume PDF was uploaded again to verify repeatability.

### Results

- Resume upload: Successful
- PDF text extraction: Successful
- Name extraction: Successful
- Email extraction: Successful
- Phone extraction: Successful
- Education extraction: Successful
- Skills extraction: Successful
- Experience extraction: Successful
- Projects extraction: Successful
- Certifications extraction: Successful
- Achievements extraction: Successful
- Languages extraction: Successful
- Structured JSON generation: Successful
- Candidate profile JSON storage: Successful

### Status

PASS

---

## Sample Structured Output

The LLM generates structured candidate information in JSON format:

```json
{
    "name": "Candidate Name",
    "email": "candidate@example.com",
    "phone": "XXXXXXXXXX",
    "education": [],
    "skills": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "achievements": [],
    "languages": []
}