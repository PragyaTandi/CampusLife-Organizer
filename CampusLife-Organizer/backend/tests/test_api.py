import uuid

from fastapi.testclient import TestClient

from backend.app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_and_me():
    email = f"newstudent{uuid.uuid4().hex[:6]}@example.com"
    payload = {"email": email, "password": "campus123", "full_name": "New Student"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]


def test_leave_validation_bad_dates():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    leave = client.post(
        "/api/leaves",
        json={"leave_type": "Medical", "start_date": "2026-10-20", "end_date": "2026-10-18", "reason": "Need time for a medical appointment and recovery period."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leave.status_code == 200
    leave_id = leave.json()["id"]
    result = client.post(f"/api/leaves/{leave_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 200
    validation = result.json()["validation"]
    assert validation["status"] in {"Needs Information", "Pending Approval"}
    assert any(check["check_name"] == "date_consistency" and check["status"] == "failed" for check in validation["checks"])


def test_ai_verify_endpoint():
    login = client.post("/api/auth/login", json={"email": "staff@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    response = client.post("/api/ai/verify?task=leave_review", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "checks" in response.json()


def test_listings_and_marketplace_interest():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    response = client.post(
        "/api/listings",
        json={"title": "Used Physics Lab Notebook", "description": "Good condition lab notebook with solved examples.", "category": "Books", "condition": "Good", "price": 350},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    listing_id = response.json()["id"]
    interest = client.post(f"/api/listings/{listing_id}/interest?message=I%20am%20interested", headers={"Authorization": f"Bearer {token}"})
    assert interest.status_code == 200
    assert interest.json()["status"] == "interest_recorded"
