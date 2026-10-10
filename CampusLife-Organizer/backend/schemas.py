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


class DashboardSummary(BaseModel):
    total_leaves: int
    approved_leaves: int
    pending_reviews: int
    total_items: int
    marketplace_listings: int
    notifications: int
