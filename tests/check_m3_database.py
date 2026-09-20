import sys
import os

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from app.app import app
from app.models import (
    db,
    M3SkillGapAnalysis,
    M3ResumeCoverLetter,
    M3InterviewPreparation,
    CareerConversationMessage
)


with app.app_context():

    print("=" * 60)
    print("M3 DATABASE VERIFICATION")
    print("=" * 60)

    skill_gap_count = M3SkillGapAnalysis.query.count()
    resume_count = M3ResumeCoverLetter.query.count()
    interview_count = M3InterviewPreparation.query.count()
    conversation_count = CareerConversationMessage.query.count()

    print()
    print("M3.1 Skill Gap records:", skill_gap_count)
    print("M3.2 Resume/Cover Letter records:", resume_count)
    print("M3.3 Interview records:", interview_count)
    print("M3.4 Conversation messages:", conversation_count)

    print()

    if skill_gap_count > 0:
        print("M3.1 database storage: PASS")
    else:
        print("M3.1 database storage: NO RECORDS")

    if resume_count > 0:
        print("M3.2 database storage: PASS")
    else:
        print("M3.2 database storage: NO RECORDS")

    if interview_count > 0:
        print("M3.3 database storage: PASS")
    else:
        print("M3.3 database storage: NO RECORDS")

    if conversation_count > 0:
        print("M3.4 database storage: PASS")
    else:
        print("M3.4 database storage: NO RECORDS")

    print()
    print("=" * 60)