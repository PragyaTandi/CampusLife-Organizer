from __future__ import annotations

from datetime import datetime
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

load_dotenv()

from backend.ai_adapter import get_ai_provider, run_ai_verification
from backend.campus_features import build_event_agenda, forecast_campus_demand, match_student_profiles
from backend.database import get_db, init_db
from backend.models import (
    AIExecution,
    CampusEvent,
    GigListing,
    LeaveApplication,
    LeaveReview,
    ListingReport,
    ListingInterest,
    LostFoundItem,
    LostFoundClaim,
    MarketplaceListing,
    Notification,
    StudentSkillProfile,
    User,
    VerificationCheck,
)
from backend.schemas import (
    DashboardSummary,
    EventCreate,
    GigCreate,
    ItemCreate,
    ItemClaimCreate,
    LeaveCreate,
    ListingCreate,
    ListingReportCreate,
    ListingStatusUpdate,
    ListingUpdate,
    LoginRequest,
    SkillProfileCreate,
    SmartFlowForecastRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from backend.services import (
    create_verification_record,
    generate_dashboard_summary,
    hash_password,
    log_event,
    match_lost_item,
    seed_demo_data,
    validate_leave,
    verify_password,
)

app = FastAPI(title="CampusOS API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
seed_db = next(get_db())
seed_demo_data(seed_db)
seed_db.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    db = next(get_db())
    seed_demo_data(db)
    db.close()


def get_current_user(db: Session = Depends(get_db), authorization: str | None = Header(default=None, alias="Authorization")) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        user = db.query(User).filter(User.email == "student@campusos.edu").first()
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user
    token = authorization.split(" ", 1)[1]
    user = db.query(User).filter(User.email == token).first()
    if not user:
        for fallback_email in ["student@campusos.edu", "staff@campusos.edu"]:
            if token.endswith(fallback_email):
                user = db.query(User).filter(User.email == fallback_email).first()
                break
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "CampusOS backend is running"}


@app.post("/api/smartflow/forecast")
def smartflow_forecast(
    payload: SmartFlowForecastRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    del current_user
    return forecast_campus_demand(payload.model_dump())


@app.put("/api/quietcollab/profile")
def save_skill_profile(
    payload: SkillProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = db.query(StudentSkillProfile).filter(StudentSkillProfile.user_id == current_user.id).first()
    if not profile:
        profile = StudentSkillProfile(user_id=current_user.id)
        db.add(profile)
    profile.skills = [skill.strip() for skill in payload.skills if skill.strip()]
    profile.interests = [interest.strip() for interest in payload.interests if interest.strip()]
    profile.availability = payload.availability.strip()
    profile.project_goal = payload.project_goal.strip()
    db.commit()
    return {"status": "saved", "skill_count": len(profile.skills)}


@app.get("/api/quietcollab/matches")
def quietcollab_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = db.query(StudentSkillProfile).filter(StudentSkillProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=409, detail="Create your skills profile before finding teammates")
    target = {
        "skills": profile.skills,
        "interests": profile.interests,
        "availability": profile.availability,
        "project_goal": profile.project_goal,
    }
    candidates = (
        db.query(StudentSkillProfile, User)
        .join(User, StudentSkillProfile.user_id == User.id)
        .filter(StudentSkillProfile.user_id != current_user.id, User.role == "student")
        .all()
    )
    matches = match_student_profiles(target, [{
        "user_id": user.id,
        "name": user.full_name,
        "skills": skill_profile.skills,
        "interests": skill_profile.interests,
        "availability": skill_profile.availability,
        "project_goal": skill_profile.project_goal,
    } for skill_profile, user in candidates])
    return {"matches": matches}


@app.post("/api/hackasync/events")
def create_campus_event(
    payload: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        agenda = build_event_agenda(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    event = CampusEvent(
        organizer_id=current_user.id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        agenda=agenda,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "title": event.title, "agenda": event.agenda}


@app.get("/api/hackasync/events")
def list_campus_events(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    events = db.query(CampusEvent).order_by(CampusEvent.starts_at.asc()).all()
    return [{
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "agenda": event.agenda,
    } for event in events]


@app.post("/api/pocketpal/gigs")
def create_gig(
    payload: GigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    gig = GigListing(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        location=payload.location,
        price=payload.price,
        status="open",
    )
    db.add(gig)
    db.commit()
    db.refresh(gig)
    return {"id": gig.id, "status": gig.status}


@app.get("/api/pocketpal/gigs")
def list_gigs(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    query = db.query(GigListing).filter(GigListing.status == "open")
    if category:
        query = query.filter(GigListing.category == category)
    gigs = query.order_by(GigListing.created_at.desc()).all()
    return [{
        "id": gig.id,
        "title": gig.title,
        "description": gig.description,
        "category": gig.category,
        "location": gig.location,
        "price": gig.price,
        "status": gig.status,
    } for gig in gigs]


@app.post("/api/auth/register", response_model=UserRead)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), full_name=payload.full_name, role="student")
    db.add(user)
    db.commit()
    db.refresh(user)
    log_event(db, user.id, "register", "user", user.id, {"email": payload.email})
    db.commit()
    return user


@app.post("/api/auth/login", response_model=TokenResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = user.email
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@app.get("/api/auth/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/api/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, int]:
    return generate_dashboard_summary(db, current_user.id)


@app.get("/api/notifications")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    items = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in items
    ]


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read = True
    db.commit()
    return {"status": "read"}


@app.get("/api/leaves")
def list_leaves(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    query = db.query(LeaveApplication)
    if current_user.role == "student":
        query = query.filter(LeaveApplication.user_id == current_user.id)
    leaves = query.order_by(LeaveApplication.created_at.desc()).all()
    return [
        {
            "id": leave.id,
            "user_id": leave.user_id,
            "leave_type": leave.leave_type,
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "reason": leave.reason,
            "emergency_contact": leave.emergency_contact,
            "status": leave.status,
            "validation_report": leave.validation_report,
            "reviewer_note": leave.reviewer_note,
            "created_at": leave.created_at.isoformat(),
        }
        for leave in leaves
    ]


@app.post("/api/leaves", response_model=dict)
def create_leave(payload: LeaveCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    leave = LeaveApplication(
        user_id=current_user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        emergency_contact=payload.emergency_contact,
        status="Draft",
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    log_event(db, current_user.id, "create_leave", "leave", leave.id, {"leave_type": leave.leave_type})
    db.commit()
    return {
        "id": leave.id,
        "status": leave.status,
        "message": "Leave application drafted. Submit it for validation.",
    }


@app.get("/api/leaves/{leave_id}")
def get_leave(leave_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    if current_user.role == "student" and leave.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return {
        "id": leave.id,
        "user_id": leave.user_id,
        "leave_type": leave.leave_type,
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "reason": leave.reason,
        "emergency_contact": leave.emergency_contact,
        "status": leave.status,
        "validation_report": leave.validation_report,
        "reviewer_note": leave.reviewer_note,
    }


@app.post("/api/leaves/{leave_id}/validate")
def validate_leave_api(leave_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    if current_user.role == "student" and leave.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    result = validate_leave({
        "leave_type": leave.leave_type,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "reason": leave.reason,
    })
    leave.validation_report = result
    leave.status = result["status"] if result["status"] != "Pending Approval" else "Submitted"
    db.commit()

    ai_result = run_ai_verification("leave_validation", {
        "leave_type": leave.leave_type,
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "reason": leave.reason,
        "status": result["status"],
    })
    execution = AIExecution(task_category="leave_validation", model_provider="gemma" if ai_result.get("status") not in {"fallback", "error", "ok"} else "mock", status="completed", input_summary=leave.leave_type, output_summary=ai_result.get("summary", result["status"]), duration_ms=120)
    db.add(execution)
    db.flush()
    checks = ai_result.get("checks", result["checks"])
    create_verification_record(db, execution, checks)
    log_event(db, current_user.id, "validate_leave", "leave", leave.id, {"validation": result, "ai": ai_result})
    db.commit()
    return {"status": "ok", "validation": result, "ai": ai_result}


@app.post("/api/leaves/{leave_id}/withdraw")
def withdraw_leave(leave_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    if leave.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    leave.status = "Withdrawn"
    db.commit()
    return {"status": "withdrawn"}


@app.post("/api/leaves/{leave_id}/review")
def review_leave(leave_id: int, decision: str, comments: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    review = LeaveReview(leave_id=leave.id, reviewer_id=current_user.id, decision=decision, comments=comments)
    db.add(review)
    leave.status = decision.capitalize() if decision in {"approved", "rejected"} else "Pending Approval"
    leave.reviewer_note = comments
    db.add(Notification(user_id=leave.user_id, notification_type="leave", title="Leave request reviewed", message=f"Your request was {leave.status.lower()}: {comments}", read=False))
    db.commit()
    log_event(db, current_user.id, "review_leave", "leave", leave.id, {"decision": leave.status})
    db.commit()
    return {"status": "reviewed"}


@app.post("/api/items/lost")
def create_lost_item(payload: ItemCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    if payload.item_type != "lost":
        raise HTTPException(status_code=400, detail="This endpoint accepts lost items only")
    item = LostFoundItem(reported_by_id=current_user.id, title=payload.title, description=payload.description, category=payload.category, location=payload.location, date_seen=payload.date_seen, item_type="lost", status="open")
    db.add(item)
    db.commit()
    db.refresh(item)
    matches = match_lost_item({
        "title": payload.title,
        "description": payload.description,
        "category": payload.category,
        "location": payload.location,
        "date_seen": payload.date_seen,
        "item_type": payload.item_type,
    }, db)
    return {"id": item.id, "status": "reported", "potential_matches": matches}


@app.post("/api/items/found")
def create_found_item(payload: ItemCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    if payload.item_type != "found":
        raise HTTPException(status_code=400, detail="This endpoint accepts found items only")
    item = LostFoundItem(reported_by_id=current_user.id, title=payload.title, description=payload.description, category=payload.category, location=payload.location, date_seen=payload.date_seen, item_type="found", status="open")
    db.add(item)
    db.commit()
    db.refresh(item)
    matches = match_lost_item({
        "title": payload.title,
        "description": payload.description,
        "category": payload.category,
        "location": payload.location,
        "date_seen": payload.date_seen,
        "item_type": payload.item_type,
    }, db)
    return {"id": item.id, "status": "reported", "potential_matches": matches}


@app.get("/api/items")
def list_items(item_type: str | None = None, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    query = db.query(LostFoundItem)
    if item_type:
        query = query.filter(LostFoundItem.item_type == item_type)
    items = query.order_by(LostFoundItem.created_at.desc()).all()
    return [{
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "location": item.location,
        "item_type": item.item_type,
        "status": item.status,
        "date_seen": item.date_seen.isoformat(),
    } for item in items]


@app.get("/api/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "location": item.location,
        "item_type": item.item_type,
        "status": item.status,
        "date_seen": item.date_seen.isoformat(),
    }


@app.post("/api/items/{item_id}/matches")
def find_matches(item_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.query(LostFoundItem).filter(LostFoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    result = match_lost_item({
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "location": item.location,
        "date_seen": item.date_seen,
        "item_type": item.item_type,
    }, db)
    return {"matches": result}


@app.post("/api/items/{item_id}/claim")
def claim_found_item(
    item_id: int,
    payload: ItemClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    item = db.query(LostFoundItem).filter(
        LostFoundItem.id == item_id,
        LostFoundItem.item_type == "found",
        LostFoundItem.status == "open",
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Open found item not found")
    claim = LostFoundClaim(
        item_id=item.id,
        claimant_id=current_user.id,
        verification_response=payload.verification_response,
        status="pending",
    )
    db.add(claim)
    db.add(Notification(user_id=item.reported_by_id, notification_type="lost_found", title="Ownership claim received", message="A student requested a mediated handover. Staff verification is required.", read=False))
    db.commit()
    db.refresh(claim)
    return {"claim_id": claim.id, "status": "pending_review", "message": "Claim submitted privately for human verification."}


@app.post("/api/items/{item_id}/resolve")
def resolve_found_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    claim_id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff verification is required to resolve an item")
    item = db.query(LostFoundItem).filter(
        LostFoundItem.id == item_id,
        LostFoundItem.item_type == "found",
        LostFoundItem.status == "open",
    ).first()
    claim = db.query(LostFoundClaim).filter(
        LostFoundClaim.id == claim_id,
        LostFoundClaim.item_id == item_id,
        LostFoundClaim.status == "pending",
    ).first()
    if not item or not claim:
        raise HTTPException(status_code=404, detail="Pending item claim not found")
    item.status = "resolved"
    claim.status = "verified"
    claim.moderator_note = "Verified by authorized staff"
    db.add(Notification(user_id=claim.claimant_id, notification_type="lost_found", title="Claim verified", message="Staff verified the ownership claim. Coordinate a mediated handover.", read=False))
    db.commit()
    log_event(db, current_user.id, "resolve_lost_found", "item", item.id, {"claim_id": claim.id})
    db.commit()
    return {"status": "resolved"}


@app.post("/api/listings")
def create_listing(payload: ListingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    listing = MarketplaceListing(user_id=current_user.id, title=payload.title, description=payload.description, category=payload.category, condition=payload.condition, price=payload.price, status="active")
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "status": "listed"}


@app.get("/api/listings")
def list_listings(category: str | None = None, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    query = db.query(MarketplaceListing).filter(MarketplaceListing.status != "removed")
    if category:
        query = query.filter(MarketplaceListing.category == category)
    items = query.order_by(MarketplaceListing.created_at.desc()).all()
    return [{
        "id": item.id,
        "user_id": item.user_id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "condition": item.condition,
        "price": item.price,
        "status": item.status,
        "seller_name": item.seller.full_name,
    } for item in items]


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"id": item.id, "title": item.title, "description": item.description, "category": item.category, "condition": item.condition, "price": item.price, "status": item.status, "seller_name": item.seller.full_name}


@app.patch("/api/listings/{listing_id}")
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own listing")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    db.commit()
    return {"id": listing.id, "status": listing.status}


@app.delete("/api/listings/{listing_id}")
def delete_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id and current_user.role != "staff":
        raise HTTPException(status_code=403, detail="You can only delete your own listing")
    db.delete(listing)
    db.commit()
    return {"status": "deleted"}


@app.patch("/api/listings/{listing_id}/status")
def update_listing_status(
    listing_id: int,
    payload: ListingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.user_id != current_user.id and current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Only the listing owner can change its status")
    listing.status = payload.status
    db.commit()
    return {"status": listing.status}


@app.post("/api/listings/{listing_id}/interest")
def express_interest(listing_id: int, message: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    interest = ListingInterest(listing_id=listing.id, user_id=current_user.id, message=message or "Interested in this item")
    db.add(interest)
    db.add(Notification(user_id=listing.user_id, notification_type="marketplace", title="New listing interest", message=f"A student is interested in: {listing.title}", read=False))
    db.commit()
    return {"status": "interest_recorded"}


@app.post("/api/listings/{listing_id}/report")
def report_listing(
    listing_id: int,
    payload: ListingReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    report = ListingReport(listing_id=listing.id, reporter_id=current_user.id, reason=payload.reason)
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"report_id": report.id, "status": "pending_review"}


@app.get("/api/admin/analytics")
def admin_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, int]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    total_users = db.query(User).count()
    total_leaves = db.query(LeaveApplication).count()
    total_listings = db.query(MarketplaceListing).count()
    total_items = db.query(LostFoundItem).count()
    return {"users": total_users, "leaves": total_leaves, "listings": total_listings, "items": total_items}


@app.get("/api/admin/reviews")
def admin_reviews(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    leaves = db.query(LeaveApplication).filter(LeaveApplication.status.in_(["Submitted", "Needs Information", "Pending Approval"])).all()
    return [{
        "id": leave.id,
        "user_id": leave.user_id,
        "leave_type": leave.leave_type,
        "status": leave.status,
        "reason": leave.reason,
    } for leave in leaves]


@app.get("/api/admin/item-claims")
def admin_item_claims(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    claims = db.query(LostFoundClaim).filter(LostFoundClaim.status == "pending").order_by(LostFoundClaim.created_at.asc()).all()
    return [{
        "id": claim.id,
        "item_id": claim.item_id,
        "claimant_id": claim.claimant_id,
        "title": claim.item.title,
        "status": claim.status,
    } for claim in claims]


@app.get("/api/admin/listing-reports")
def admin_listing_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    reports = db.query(ListingReport).filter(ListingReport.status == "pending").order_by(ListingReport.created_at.asc()).all()
    return [{
        "id": report.id,
        "listing_id": report.listing_id,
        "listing_title": report.listing.title,
        "reason": report.reason,
        "status": report.status,
    } for report in reports]


@app.post("/api/admin/listing-reports/{report_id}/moderate")
def moderate_listing_report(
    report_id: int,
    action: str = Query(..., pattern="^(dismiss|remove)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    report = db.query(ListingReport).filter(ListingReport.id == report_id, ListingReport.status == "pending").first()
    if not report:
        raise HTTPException(status_code=404, detail="Pending listing report not found")
    report.status = "dismissed" if action == "dismiss" else "actioned"
    if action == "remove":
        report.listing.status = "removed"
    db.add(Notification(user_id=report.listing.user_id, notification_type="moderation", title="Listing report reviewed", message="A moderator reviewed a report on your listing.", read=False))
    log_event(db, current_user.id, "moderate_listing_report", "listing", report.listing_id, {"action": action, "report_id": report.id})
    db.commit()
    return {"status": report.status}


@app.post("/api/ai/verify")
def ai_verify(task: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    ai_result = run_ai_verification(task, {"requester": current_user.email, "task": task})
    execution = AIExecution(task_category=task, model_provider="gemma" if get_ai_provider() == "gemma" else "mock", status="completed", input_summary=task, output_summary=ai_result.get("summary", "AI verification completed."), duration_ms=150)
    db.add(execution)
    db.flush()
    checks = ai_result.get("checks", [])
    create_verification_record(db, execution, checks)
    return {"status": "ok", "checks": checks, "run_id": execution.id, "ai": ai_result}


@app.get("/api/ai/runs/{run_id}")
def get_ai_run(run_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    execution = db.query(AIExecution).filter(AIExecution.id == run_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="AI run not found")
    checks = db.query(VerificationCheck).filter(VerificationCheck.execution_id == execution.id).all()
    return {
        "id": execution.id,
        "task_category": execution.task_category,
        "status": execution.status,
        "checks": [{
            "id": check.id,
            "check_name": check.check_name,
            "status": check.status,
            "requires_review": check.requires_review,
            "explanation": check.explanation,
        } for check in checks],
    }
