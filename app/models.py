from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


# =========================================================
# USER
# =========================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

class StudentProfile(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        unique=True
    )

    candidate_name = db.Column(
        db.String(100)
    )

    candidate_email = db.Column(
        db.String(120)
    )

    education = db.Column(
        db.Text
    )

    experience = db.Column(
        db.Text
    )

    skills = db.Column(
        db.Text
    )

    projects = db.Column(
        db.Text
    )

    certifications = db.Column(
        db.Text
    )
    mobile_number = db.Column(db.String(30))
    college = db.Column(db.String(255))
    degree_branch = db.Column(db.String(255))
    graduation_year = db.Column(db.Integer)
    city = db.Column(db.String(120))
    profile_completed = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )


# =========================================================
# RESUME
# =========================================================

class Resume(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    filename = db.Column(
        db.String(255)
    )

    resume_text = db.Column(
        db.Text
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# AI ANALYSIS
# =========================================================

class AIAnalysis(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    resume_analysis = db.Column(
        db.Text
    )

    career_recommendations = db.Column(
        db.Text
    )

    skill_gap = db.Column(
        db.Text
    )

    interview_preparation = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# JOB
# =========================================================

class Job(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    job_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    title = db.Column(
        db.String(255)
    )

    company = db.Column(
        db.String(255)
    )

    category = db.Column(
        db.String(100)
    )

    description = db.Column(
        db.Text
    )

    skills = db.Column(
        db.Text
    )

    experience = db.Column(
        db.String(255)
    )

    education = db.Column(
        db.String(255)
    )

    industry = db.Column(
        db.String(255)
    )

    location = db.Column(
        db.String(255)
    )

    payrate = db.Column(
        db.String(255)
    )


# =========================================================
# JOB MATCH
# =========================================================

class JobMatch(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(
        db.String(100),
        nullable=False
    )

    compatibility_score = db.Column(
        db.Float
    )

    # -----------------------------------------------------
    # M4.3 RAG RETRIEVAL INFORMATION
    # -----------------------------------------------------

    retrieval_score = db.Column(
        db.Float
    )

    retrieval_rank = db.Column(
        db.Integer
    )

    matching_skills = db.Column(
        db.Text
    )

    missing_skills = db.Column(
        db.Text
    )

    reasoning = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# MILESTONE 3 — SKILL GAP ANALYSIS
# =========================================================

class M3SkillGapAnalysis(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(
        db.String(100),
        nullable=False
    )

    analysis = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# MILESTONE 3 — RESUME & COVER LETTER
# =========================================================

class M3ResumeCoverLetter(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(
        db.String(100),
        nullable=False
    )

    tailored_resume = db.Column(
        db.Text
    )

    cover_letter = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# MILESTONE 3 — INTERVIEW PREPARATION
# =========================================================

class M3InterviewPreparation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(
        db.String(100),
        nullable=False
    )

    interview_preparation = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# CAREER ASSISTANT — CHAT CONVERSATION
# =========================================================

class CareerConversation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        default="New Chat"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# CAREER ASSISTANT — CONVERSATION MESSAGES
# =========================================================

class CareerConversationMessage(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("career_conversation.id"),
        nullable=True
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# =========================================================
# MILESTONE 4.1 — APPLICATION TRACKER
# =========================================================

class Application(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(
        db.String(100),
        nullable=False
    )

    company = db.Column(
        db.String(255)
    )

    job_title = db.Column(
        db.String(255)
    )

    job_description = db.Column(
        db.Text
    )

    # -----------------------------------------------------
    # Application dates
    # -----------------------------------------------------

    application_date = db.Column(
        db.DateTime
    )

    deadline = db.Column(
        db.DateTime
    )

    # -----------------------------------------------------
    # M4.1 — Follow-up reminder date
    # -----------------------------------------------------

    follow_up_date = db.Column(
        db.DateTime
    )

    # -----------------------------------------------------
    # Application status
    # -----------------------------------------------------

    status = db.Column(
        db.String(50),
        default="Saved"
    )

    # -----------------------------------------------------
    # Interview information
    # -----------------------------------------------------

    interview_date = db.Column(
        db.DateTime
    )

    interview_status = db.Column(
        db.String(100)
    )

    # -----------------------------------------------------
    # Notes and follow-up information
    # -----------------------------------------------------

    notes = db.Column(
        db.Text
    )

    # -----------------------------------------------------
    # Record timestamps
    # -----------------------------------------------------

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )