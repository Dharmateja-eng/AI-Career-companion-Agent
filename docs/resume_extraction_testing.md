# Resume Extraction Testing

## Objective

The resume extraction module was tested to verify whether the system can extract structured candidate information from PDF resumes using PyPDF2 and Gemini LLM.

## Extraction Workflow

1. User uploads a PDF resume.
2. PyPDF2 extracts the text from the PDF.
3. Extracted text is sent to the Gemini LLM.
4. Gemini identifies candidate information.
5. The information is returned as structured JSON.
6. The structured profile is stored in `candidate_profile.json`.

## Test Cases

### Test Case 1 – Personal Resume

**Resume:** `resume.pdf`

**Result:** Passed

The system successfully extracted:

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

The extracted information was returned in structured JSON format.

---

### Test Case 2 – Python Developer Resume

**Resume:** `sample_resume_1_python_developer.pdf`

**Result:** Passed

The system successfully extracted:

- Name
- Email
- Phone
- Education
- CGPA and percentage
- Technical skills
- Internship experience
- Projects
- Certifications
- Achievements
- Languages

The system also correctly identified the internship company, role, year and description.

---

### Test Case 3 – Data Analyst Resume

**Resume:** `sample_resume_2_data_analyst.pdf`

**Result:** Passed

The system successfully extracted:

- Name
- Email
- Phone
- Education
- CGPA and percentage
- Technical skills
- Projects
- Certifications
- Achievements
- Languages

The resume did not contain professional experience, and the system correctly returned an empty experience list instead of inventing information.

## Testing Summary

| Test Case | Resume Type | Result |
|------------|-------------|--------|
| 1 | Personal Resume | Passed |
| 2 | Python Developer | Passed |
| 3 | Data Analyst | Passed |

## Conclusion

The resume parsing and extraction module successfully processed different resume formats and generated structured candidate profiles.

The testing demonstrates that the system can extract important candidate information such as education, skills, experience, projects, certifications, achievements and languages using PDF text extraction and an LLM.