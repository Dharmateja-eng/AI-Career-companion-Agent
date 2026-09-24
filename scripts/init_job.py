import os
import sys
import csv

# -------------------------------------------------
# Find project root
# -------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

# Make the root project available to Python
sys.path.insert(0, PROJECT_ROOT)

# Import the actual Flask application
from app.app import app
from app.models import db, Job


# -------------------------------------------------
# Dataset location
# -------------------------------------------------

CSV_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "job_postings_clean.csv"
)


# -------------------------------------------------
# Check dataset
# -------------------------------------------------

if not os.path.exists(CSV_FILE):
    print("ERROR: Dataset not found!")
    print(CSV_FILE)
    raise SystemExit


# -------------------------------------------------
# Import jobs into database
# -------------------------------------------------

with app.app_context():

    print("Starting job database import...")
    print("Database:", app.config["SQLALCHEMY_DATABASE_URI"])
    print("CSV file:", CSV_FILE)

    count = 0

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        print("\nCSV columns:")
        print(reader.fieldnames)

        for row in reader:

            # -----------------------------------------
            # Job ID
            # -----------------------------------------

            job_id = (
                row.get("jobid")
                or row.get("job_id")
                or row.get("JobId")
                or row.get("id")
                or ""
            ).strip()

            if not job_id:
                continue

            # -----------------------------------------
            # Avoid duplicate jobs
            # -----------------------------------------

            existing_job = Job.query.filter_by(
                job_id=str(job_id)
            ).first()

            if existing_job:
                continue

            # -----------------------------------------
            # Create Job
            # -----------------------------------------

            job = Job(

                job_id=str(job_id),

                title=(
                    row.get("jobtitle")
                    or row.get("title")
                    or row.get("job_title")
                    or ""
                ).strip(),

                company=(
                    row.get("company")
                    or row.get("Company")
                    or ""
                ).strip(),

                category=(
                    row.get("category")
                    or row.get("Category")
                    or ""
                ).strip(),

                description=(
                    row.get("jobdescription")
                    or row.get("description")
                    or row.get("job_description")
                    or ""
                ).strip(),

                skills=(
                    row.get("skills")
                    or row.get("Key Skills")
                    or row.get("key_skills")
                    or ""
                ).strip(),

                experience=(
                    row.get("experience")
                    or row.get("Job Experience Required")
                    or row.get("experience_required")
                    or ""
                ).strip(),

                education=(
                    row.get("education")
                    or row.get("Education")
                    or ""
                ).strip(),

                industry=(
                    row.get("industry")
                    or row.get("Industry")
                    or ""
                ).strip(),

                location=(
                    row.get("joblocation_address")
                    or row.get("location")
                    or ""
                ).strip(),

                payrate=(
                    row.get("payrate")
                    or row.get("salary")
                    or row.get("Salary")
                    or ""
                ).strip()
            )

            db.session.add(job)
            count += 1

    # -----------------------------------------
    # Save all jobs
    # -----------------------------------------

    db.session.commit()

    print("\nSuccessfully imported", count, "jobs.")
    print("Job database import completed!")