from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LeaveCreate(BaseModel):
    leave_type: str = Field(..., min_length=2)
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=10)
    emergency_contact: str | None = None


class LeaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    emergency_contact: str | None = None
    status: str
    validation_report: dict[str, Any] | None = None
    reviewer_note: str | None = None
    created_at: datetime


class ItemCreate(BaseModel):
    title: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)
    category: str
    location: str
    date_seen: date
    item_type: Literal["lost", "found"]


class ListingCreate(BaseModel):
    title: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)
    category: str
    condition: str
    price: float


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=64)
    condition: str | None = Field(default=None, min_length=2, max_length=32)
    price: float | None = Field(default=None, ge=0, le=100000)


class ListingStatusUpdate(BaseModel):
    status: Literal["active", "reserved", "sold"]


class ListingReportCreate(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class ItemClaimCreate(BaseModel):
    verification_response: str = Field(..., min_length=5, max_length=1000)


class DashboardSummary(BaseModel):
    total_leaves: int
    approved_leaves: int
    pending_reviews: int
    total_items: int
    marketplace_listings: int
    notifications: int


class CounterCapacity(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    service_rate_per_minute: float = Field(..., gt=0, le=20)


class SmartFlowForecastRequest(BaseModel):
    class_end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    students_finishing: int = Field(..., gt=0, le=5000)
    visit_probability: float = Field(..., ge=0, le=1)
    average_walk_minutes: int = Field(6, ge=1, le=60)
    walk_time_spread_minutes: int = Field(3, ge=0, le=30)
    forecast_minutes: int = Field(30, ge=10, le=180)
    counters: list[CounterCapacity] = Field(..., min_length=1, max_length=20)


class SkillProfileCreate(BaseModel):
    skills: list[str] = Field(..., min_length=1, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=20)
    availability: str = Field("Flexible", max_length=128)
    project_goal: str = Field("", max_length=255)


class EventCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field("", max_length=2000)
    starts_at: datetime
    ends_at: datetime
    setup_minutes: int = Field(30, ge=0, le=240)
    break_minutes: int = Field(15, ge=0, le=120)
    judging_minutes: int = Field(60, ge=0, le=360)
    submission_minutes_before_end: int = Field(30, ge=0, le=240)


class GigCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    category: str = Field(..., min_length=2, max_length=64)
    location: str = Field("Campus", max_length=128)
    price: float = Field(..., ge=0, le=100000)
