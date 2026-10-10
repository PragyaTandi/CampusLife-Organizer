from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="student")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    leaves = relationship("LeaveApplication", back_populates="user")
    lost_items = relationship("LostFoundItem", back_populates="reporter")
    listings = relationship("MarketplaceListing", back_populates="seller")
    notifications = relationship("Notification", back_populates="user")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    department = Column(String(128), default="Computer Science")
    year = Column(String(16), default="2nd Year")
    enrollment_no = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)


class LeaveApplication(Base):
    __tablename__ = "leave_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(String(64), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    emergency_contact = Column(String(128), nullable=True)
    status = Column(String(64), default="Draft")
    reviewer_note = Column(Text, nullable=True)
    validation_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="leaves")
    reviews = relationship("LeaveReview", back_populates="leave")


class LeaveReview(Base):
    __tablename__ = "leave_reviews"

    id = Column(Integer, primary_key=True, index=True)
    leave_id = Column(Integer, ForeignKey("leave_applications.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String(32), default="pending")
    comments = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    leave = relationship("LeaveApplication", back_populates="reviews")


class LostFoundItem(Base):
    __tablename__ = "lost_found_items"

    id = Column(Integer, primary_key=True, index=True)
    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    location = Column(String(128), nullable=False)
    date_seen = Column(Date, nullable=False)
    item_type = Column(String(12), default="lost")
    status = Column(String(32), default="open")
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reporter = relationship("User", back_populates="lost_items")
    matches = relationship("ItemMatch", foreign_keys="ItemMatch.item_id", back_populates="item")
    matched_relations = relationship("ItemMatch", foreign_keys="ItemMatch.matched_item_id", back_populates="matched_item")


class ItemMatch(Base):
    __tablename__ = "item_matches"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("lost_found_items.id"), nullable=False)
    matched_item_id = Column(Integer, ForeignKey("lost_found_items.id"), nullable=False)
    score = Column(Float, default=0.0)
    reason = Column(Text, default="")
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    item = relationship("LostFoundItem", foreign_keys=[item_id], back_populates="matches")
    matched_item = relationship("LostFoundItem", foreign_keys=[matched_item_id], back_populates="matched_relations")


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    condition = Column(String(32), default="Good")
    price = Column(Float, default=0.0)
    status = Column(String(32), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller = relationship("User", back_populates="listings")


class ListingInterest(Base):
    __tablename__ = "listing_interests"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(64), default="general")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(120), nullable=False)
    entity_type = Column(String(120), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIExecution(Base):
    __tablename__ = "ai_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_category = Column(String(100), default="general")
    model_provider = Column(String(80), default="mock")
    status = Column(String(32), default="completed")
    input_summary = Column(Text, default="")
    output_summary = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    checks = relationship("VerificationCheck", back_populates="execution")


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("ai_executions.id"), nullable=False)
    check_name = Column(String(120), nullable=False)
    status = Column(String(32), default="not_checked")
    explanation = Column(Text, default="")
    evidence = Column(JSON, default=list)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    execution = relationship("AIExecution", back_populates="checks")
