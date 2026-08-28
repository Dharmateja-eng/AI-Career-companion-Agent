# Candidate / Student Profile Data Model

## 1. Purpose

The candidate profile stores structured information extracted from a student's
resume.

The structured profile provides a consistent representation of the candidate
and can be used by future modules such as job-resume matching, skill-gap
analysis, interview preparation, and career assistance.

## 2. Profile Structure

### Personal Information

- Name
- Email
- Phone

### Education

- Degree
- Institution
- Field of Study
- Graduation Year

### Skills

- Technical Skills
- Soft Skills

### Experience

- Company
- Job Role
- Duration
- Description

### Projects

- Project Name
- Technologies Used
- Description

### Certifications

- Certification Name
- Issuing Organization
- Date

### Achievements

- Achievement
- Description

### Interests

- Interest

## 3. Example Structured Profile

```json
{
  "personal_information": {
    "name": "Student Name",
    "email": "student@example.com",
    "phone": "XXXXXXXXXX"
  },
  "education": [
    {
      "degree": "B.Tech",
      "institution": "Example University",
      "field_of_study": "Artificial Intelligence and Machine Learning",
      "graduation_year": "2029"
    }
  ],
  "skills": {
    "technical": [
      "Python",
      "SQL",
      "Machine Learning"
    ],
    "soft": [
      "Communication",
      "Teamwork"
    ]
  },
  "experience": [],
  "projects": [
    {
      "name": "Example Project",
      "technologies": [
        "Python",
        "Flask"
      ],
      "description": "Example project description"
    }
  ],
  "certifications": [],
  "achievements": [],
  "interests": []
}