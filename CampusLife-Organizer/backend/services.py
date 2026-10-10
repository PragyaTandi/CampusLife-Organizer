from __future__ import annotations

from datetime import date, datetime
from typing import Any

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.campus_features import build_event_agenda
from backend.models import (
    AIExecution,
    AuditEvent,
    CampusEvent,
    GigListing,
    LeaveApplication,
    LostFoundItem,
    MarketplaceListing,
    Notification,
    StudentSkillProfile,
    User,
    VerificationCheck,
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def validate_leave(leave_data: dict[str, Any]) -> dict[str, Any]:
    start_date = leave_data.get("start_date")
    end_date = leave_data.get("end_date")
    reason = leave_data.get("reason") or ""
    leave_type = leave_data.get("leave_type") or ""

    checks: list[dict[str, Any]] = []

    if start_date and end_date:
        if end_date < start_date:
            checks.append({
                "check_name": "date_consistency",
                "status": "failed",
                "explanation": "End date is earlier than the start date.",
                "evidence": ["start_date", "end_date"],
                "requires_review": True,
            })
        else:
            checks.append({
                "check_name": "date_consistency",
                "status": "passed",
                "explanation": "The end date is not earlier than the start date.",
                "evidence": ["start_date", "end_date"],
                "requires_review": False,
            })
    else:
        checks.append({
            "check_name": "date_consistency",
            "status": "not_checked",
            "explanation": "Dates were not fully provided.",
            "evidence": [],
            "requires_review": False,
        })

    if leave_type:
        checks.append({
            "check_name": "leave_type_valid",
            "status": "passed",
            "explanation": f"Leave type '{leave_type}' was submitted.",
            "evidence": ["leave_type"],
            "requires_review": False,
        })
    else:
        checks.append({
            "check_name": "leave_type_valid",
            "status": "failed",
            "explanation": "Leave type is required.",
            "evidence": ["leave_type"],
            "requires_review": True,
        })

    if reason and len(reason.strip()) >= 10:
        checks.append({
            "check_name": "reason_provided",
            "status": "passed",
            "explanation": "A meaningful reason was provided.",
            "evidence": ["reason"],
            "requires_review": False,
        })
    else:
        checks.append({
            "check_name": "reason_provided",
            "status": "failed",
            "explanation": "A more detailed reason is required.",
            "evidence": ["reason"],
            "requires_review": True,
        })

    passed = sum(1 for c in checks if c["status"] == "passed")
    failed = sum(1 for c in checks if c["status"] == "failed")
    needs_review = sum(1 for c in checks if c["status"] in {"needs_review", "failed"})

    status = "Pending Approval" if failed == 0 and needs_review == 0 else "Needs Information"
    if failed > 0:
        status = "Needs Information"

    return {
        "status": status,
        "checks": checks,
        "summary": {
            "passed": passed,
            "failed": failed,
            "needs_review": needs_review,
        },
    }


def match_lost_item(item: dict[str, Any], db: Session) -> list[dict[str, Any]]:
    target_type = "found" if item.get("item_type", "lost") == "lost" else "lost"
    all_items = db.query(LostFoundItem).filter(
        LostFoundItem.item_type == target_type,
        LostFoundItem.status != "resolved",
    ).all()
    matches: list[dict[str, Any]] = []
    for candidate in all_items:
        score = 0
        if candidate.category.lower() == item.get("category", "").lower():
            score += 30
        if candidate.location.lower() == item.get("location", "").lower():
            score += 20
        title_tokens = set(item.get("title", "").lower().split())
        candidate_title_tokens = set(candidate.title.lower().split())
        if title_tokens or candidate_title_tokens:
            score += round(20 * len(title_tokens & candidate_title_tokens) / max(1, len(title_tokens | candidate_title_tokens)))
        description_tokens = set(item.get("description", "").lower().split())
        candidate_description_tokens = set(candidate.description.lower().split())
        if description_tokens or candidate_description_tokens:
            score += round(20 * len(description_tokens & candidate_description_tokens) / max(1, len(description_tokens | candidate_description_tokens)))
        item_date = item.get("date_seen")
        if item_date:
            if isinstance(item_date, str):
                item_date = date.fromisoformat(item_date)
            days_apart = abs((candidate.date_seen - item_date).days)
            score += max(0, 10 - days_apart * 2)
        matches.append({
            "id": candidate.id,
            "title": candidate.title,
            "category": candidate.category,
            "location": candidate.location,
            "score": min(score, 100),
            "reason": f"Compared category, visible description, location, and approximate date. Candidate near {candidate.location}; similarity is not proof of ownership.",
        })
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:5]


def generate_dashboard_summary(db: Session, user_id: int) -> dict[str, Any]:
    leaves = db.query(LeaveApplication).filter(LeaveApplication.user_id == user_id).count()
    approved = db.query(LeaveApplication).filter(LeaveApplication.user_id == user_id, LeaveApplication.status == "Approved").count()
    pending_reviews = db.query(LeaveApplication).filter(LeaveApplication.user_id == user_id, LeaveApplication.status.in_(["Pending Approval", "Needs Information"])).count()
    listings = db.query(MarketplaceListing).filter(MarketplaceListing.user_id == user_id).count()
    items = db.query(LostFoundItem).filter(LostFoundItem.reported_by_id == user_id).count()
    notifications = db.query(Notification).filter(Notification.user_id == user_id, Notification.read == False).count()
    return {
        "total_leaves": leaves,
        "approved_leaves": approved,
        "pending_reviews": pending_reviews,
        "total_items": items,
        "marketplace_listings": listings,
        "notifications": notifications,
    }


def log_event(db: Session, user_id: int, action: str, entity_type: str, entity_id: int | None, details: dict[str, Any] | None = None) -> None:
    db.add(AuditEvent(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


def seed_demo_data(db: Session) -> None:
    admin = db.query(User).filter(User.email == "staff@campusos.edu").first()
    if not admin:
        admin = User(email="staff@campusos.edu", password_hash=hash_password("campus123"), full_name="Maya Ross", role="staff")
        db.add(admin)
    student = db.query(User).filter(User.email == "student@campusos.edu").first()
    if not student:
        student = User(email="student@campusos.edu", password_hash=hash_password("campus123"), full_name="Ari Sharma", role="student")
        db.add(student)
    db.flush()

    if db.query(LeaveApplication).count() == 0:
        db.add_all([
            Notification(user_id=student.id, notification_type="leave", title="Leave status", message="Your leave request is pending approval.", read=False),
            Notification(user_id=student.id, notification_type="marketplace", title="Marketplace interest", message="Someone showed interest in your calculator listing.", read=False),
            LeaveApplication(user_id=student.id, leave_type="Medical", start_date=date(2026, 10, 18), end_date=date(2026, 10, 20), reason="I have a clinic visit and need rest time.", emergency_contact="+91 98765 43210", status="Pending Approval", validation_report={"checks": ["date_consistency", "reason_provided"]}),
            LostFoundItem(reported_by_id=student.id, title="Black scientific calculator", description="Black calculator with a blue sticker on the back and case.", category="Electronics", location="Library", date_seen=date(2026, 10, 12), item_type="lost", status="open"),
            LostFoundItem(reported_by_id=admin.id, title="Black scientific calculator", description="Found near the library study desk on the evening of 12 Oct.", category="Electronics", location="Library", date_seen=date(2026, 10, 12), item_type="found", status="open"),
            MarketplaceListing(user_id=student.id, title="Used Engineering Calculator", description="Good condition calculator for core engineering courses.", category="Electronics", condition="Good", price=1200.0, status="active"),
        ])

    second_student = db.query(User).filter(User.email == "rohan@campusos.edu").first()
    if not second_student:
        second_student = User(
            email="rohan@campusos.edu",
            password_hash=hash_password("campus123"),
            full_name="Rohan Mehta",
            role="student",
        )
        db.add(second_student)
        db.flush()

    for profile_user, skills, interests, goal, availability in [
        (student, ["Python", "Machine learning"], ["AI", "Climate tech"], "Build an AI campus assistant", "Weekends"),
        (second_student, ["React", "UI design"], ["AI", "Hackathons"], "Build an AI campus assistant", "Evenings"),
    ]:
        profile = db.query(StudentSkillProfile).filter(StudentSkillProfile.user_id == profile_user.id).first()
        if not profile:
            db.add(StudentSkillProfile(
                user_id=profile_user.id,
                skills=skills,
                interests=interests,
                project_goal=goal,
                availability=availability,
            ))

    demo_event = db.query(CampusEvent).filter(CampusEvent.title == "Campus Build Weekend").first()
    if not demo_event:
        starts_at = datetime(2026, 11, 14, 9, 0)
        ends_at = datetime(2026, 11, 14, 18, 0)
        agenda = build_event_agenda({
            "starts_at": starts_at,
            "ends_at": ends_at,
            "setup_minutes": 30,
            "break_minutes": 20,
            "judging_minutes": 60,
            "submission_minutes_before_end": 30,
        })
        db.add(CampusEvent(
            organizer_id=admin.id,
            title="Campus Build Weekend",
            description="Demo event agenda generated from sample assumptions.",
            starts_at=starts_at,
            ends_at=ends_at,
            agenda=agenda,
        ))
    elif not demo_event.agenda:
        demo_event.agenda = build_event_agenda({
            "starts_at": demo_event.starts_at,
            "ends_at": demo_event.ends_at,
            "setup_minutes": 30,
            "break_minutes": 20,
            "judging_minutes": 60,
            "submission_minutes_before_end": 30,
        })
    if db.query(GigListing).count() == 0:
        db.add(GigListing(
            user_id=second_student.id,
            title="Pick up printed notes",
            description="Can collect printed notes from the campus shop this afternoon.",
            category="Errand",
            location="Main quad",
            price=40,
            status="open",
        ))
    db.commit()


def create_verification_record(db: Session, execution: AIExecution, checks: list[dict[str, Any]]) -> None:
    for item in checks:
        db.add(VerificationCheck(
            execution_id=execution.id,
            check_name=item.get("check_name", "unknown"),
            status=item.get("status", "not_checked"),
            explanation=item.get("explanation", ""),
            evidence=item.get("evidence", []),
            requires_review=bool(item.get("requires_review", False)),
        ))
    db.commit()
