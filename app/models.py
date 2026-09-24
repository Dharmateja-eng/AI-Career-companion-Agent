from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
        unique=True
    )
    education = db.Column(db.Text)
    experience = db.Column(db.Text)
    skills = db.Column(db.Text)
    projects = db.Column(db.Text)
    certifications = db.Column(db.Text)


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    filename = db.Column(db.String(255))
    resume_text = db.Column(db.Text)
    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class AIAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    resume_analysis = db.Column(db.Text)
    career_recommendations = db.Column(db.Text)
    skill_gap = db.Column(db.Text)
    interview_preparation = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )
    title = db.Column(db.String(255))
    company = db.Column(db.String(255))
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    skills = db.Column(db.Text)
    experience = db.Column(db.String(255))
    education = db.Column(db.String(255))
    industry = db.Column(db.String(255))
    location = db.Column(db.String(255))
    payrate = db.Column(db.String(255))


class JobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )
    job_id = db.Column(
        db.String(100),
        nullable=False
    )
    compatibility_score = db.Column(db.Float)
    matching_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    reasoning = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
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
class CareerConversationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
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