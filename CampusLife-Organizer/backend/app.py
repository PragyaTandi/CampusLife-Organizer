from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import get_db, init_db
from backend.models import (
    AIExecution,
    LeaveApplication,
    LeaveReview,
    ListingInterest,
    LostFoundItem,
    MarketplaceListing,
    Notification,
    User,
    VerificationCheck,
)
from backend.schemas import (
    DashboardSummary,
    ItemCreate,
    LeaveCreate,
    ListingCreate,
    LoginRequest,
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

    execution = AIExecution(task_category="leave_validation", model_provider="mock", status="completed", input_summary=leave.leave_type, output_summary=result["status"], duration_ms=120)
    db.add(execution)
    db.flush()
    create_verification_record(db, execution, result["checks"])
    log_event(db, current_user.id, "validate_leave", "leave", leave.id, result)
    db.commit()
    return {"status": "ok", "validation": result}


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
    return {"id": item.id, "status": "reported"}


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
    }, db)
    return {"matches": result}


@app.post("/api/listings")
def create_listing(payload: ListingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    listing = MarketplaceListing(user_id=current_user.id, title=payload.title, description=payload.description, category=payload.category, condition=payload.condition, price=payload.price, status="active")
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"id": listing.id, "status": "listed"}


@app.get("/api/listings")
def list_listings(category: str | None = None, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    query = db.query(MarketplaceListing)
    if category:
        query = query.filter(MarketplaceListing.category == category)
    items = query.order_by(MarketplaceListing.created_at.desc()).all()
    return [{
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "category": item.category,
        "condition": item.condition,
        "price": item.price,
        "status": item.status,
    } for item in items]


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"id": item.id, "title": item.title, "description": item.description, "category": item.category, "condition": item.condition, "price": item.price, "status": item.status}


@app.post("/api/listings/{listing_id}/interest")
def express_interest(listing_id: int, message: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    interest = ListingInterest(listing_id=listing.id, user_id=current_user.id, message=message or "Interested in this item")
    db.add(interest)
    db.commit()
    return {"status": "interest_recorded"}


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


@app.post("/api/ai/verify")
def ai_verify(task: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    execution = AIExecution(task_category=task, model_provider="mock", status="completed", input_summary=task, output_summary="Mock AI verification completed.", duration_ms=150)
    db.add(execution)
    db.flush()
    checks = [
        {"check_name": "task_scope", "status": "passed", "explanation": "Task was scoped to the requested operation.", "evidence": ["task"], "requires_review": False},
        {"check_name": "risk_review", "status": "needs_review", "explanation": "Human approval may still be required for institution-level decisions.", "evidence": ["final_decision"], "requires_review": True},
    ]
    create_verification_record(db, execution, checks)
    return {"status": "ok", "checks": checks, "run_id": execution.id}


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
