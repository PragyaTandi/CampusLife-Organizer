import uuid

from fastapi.testclient import TestClient

from backend.app import app
from backend.campus_features import build_event_agenda, forecast_campus_demand

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


def test_smartflow_forecast_uses_explicit_assumptions():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    response = client.post(
        "/api/smartflow/forecast",
        json={
            "class_end_time": "13:00",
            "students_finishing": 200,
            "visit_probability": 0.7,
            "average_walk_minutes": 6,
            "walk_time_spread_minutes": 3,
            "forecast_minutes": 30,
            "counters": [
                {"name": "North", "service_rate_per_minute": 0.8},
                {"name": "South", "service_rate_per_minute": 0.7},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["expected_visitors"] == 140
    assert round(sum(bucket["expected_arrivals"] for bucket in result["arrival_curve"])) == 140
    assert result["confidence"] == "low"
    assert "not live" in result["data_label"]
    assert result["recommendations"]


def test_smartflow_forecast_respects_midnight_boundary_and_zero_spread():
    result = forecast_campus_demand({
        "class_end_time": "23:55",
        "students_finishing": 10,
        "visit_probability": 0.5,
        "average_walk_minutes": 3,
        "walk_time_spread_minutes": 0,
        "forecast_minutes": 15,
        "counters": [{"name": "One counter", "service_rate_per_minute": 1}],
    })
    assert result["expected_visitors"] == 5
    assert sum(bucket["expected_arrivals"] for bucket in result["arrival_curve"]) == 5
    assert all(":" in point["time"] for point in result["arrival_curve"])


def test_quietcollab_profile_and_match_flow():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.put(
        "/api/quietcollab/profile",
        json={
            "skills": ["Python", "Machine learning"],
            "interests": ["AI", "Climate tech"],
            "availability": "Weekends",
            "project_goal": "Build an AI campus assistant",
        },
        headers=headers,
    )
    assert saved.status_code == 200
    matches = client.get("/api/quietcollab/matches", headers=headers)
    assert matches.status_code == 200
    assert matches.json()["matches"]
    assert "starter" in matches.json()["matches"][0]


def test_hackasync_creates_agenda_and_rejects_invalid_times():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    event = {
        "title": f"Test event {uuid.uuid4().hex[:6]}",
        "description": "A test event for schedule creation.",
        "starts_at": "2026-11-14T09:00:00",
        "ends_at": "2026-11-14T18:00:00",
        "setup_minutes": 30,
        "break_minutes": 20,
        "judging_minutes": 60,
        "submission_minutes_before_end": 30,
    }
    created = client.post("/api/hackasync/events", json=event, headers=headers)
    assert created.status_code == 200
    assert created.json()["agenda"]
    assert any(item["title"] == "Judging" for item in created.json()["agenda"])
    event["ends_at"] = "2026-11-14T08:00:00"
    invalid = client.post("/api/hackasync/events", json=event, headers=headers)
    assert invalid.status_code == 422


def test_short_event_agenda_has_ordered_times():
    from datetime import datetime

    agenda = build_event_agenda({
        "starts_at": datetime(2026, 11, 14, 9, 0),
        "ends_at": datetime(2026, 11, 14, 9, 20),
        "setup_minutes": 30,
        "break_minutes": 20,
        "judging_minutes": 60,
        "submission_minutes_before_end": 30,
    })
    for item in agenda:
        assert item["starts_at"] <= item["ends_at"]


def test_pocketpal_gig_creation_and_listing():
    login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    token = login.json()["access_token"]
    created = client.post(
        "/api/pocketpal/gigs",
        json={
            "title": f"Campus errand {uuid.uuid4().hex[:6]}",
            "description": "Deliver a sealed print order to a campus dorm.",
            "category": "Errand",
            "location": "Main quad",
            "price": 50,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 200
    gigs = client.get("/api/pocketpal/gigs")
    assert gigs.status_code == 200
    assert any(gig["id"] == created.json()["id"] for gig in gigs.json())


def test_lost_found_reports_match_both_directions_and_claim_needs_staff_resolution():
    student_login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    report = client.post(
        "/api/items/found",
        json={
            "title": f"Red umbrella {uuid.uuid4().hex[:4]}",
            "description": "Red umbrella with a wooden handle.",
            "category": "Personal items",
            "location": "Library",
            "date_seen": "2026-10-10",
            "item_type": "found",
        },
        headers=student_headers,
    )
    assert report.status_code == 200
    assert "potential_matches" in report.json()

    claim = client.post(
        f"/api/items/{report.json()['id']}/claim",
        json={"verification_response": "There is a small scratch under the handle."},
        headers=student_headers,
    )
    assert claim.status_code == 200
    assert claim.json()["status"] == "pending_review"
    assert client.post(
        f"/api/items/{report.json()['id']}/resolve?claim_id={claim.json()['claim_id']}",
        headers=student_headers,
    ).status_code == 403

    staff_login = client.post("/api/auth/login", json={"email": "staff@campusos.edu", "password": "campus123"})
    staff_headers = {"Authorization": f"Bearer {staff_login.json()['access_token']}"}
    resolved = client.post(
        f"/api/items/{report.json()['id']}/resolve?claim_id={claim.json()['claim_id']}",
        headers=staff_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_marketplace_owner_controls_and_report_moderation():
    student_login = client.post("/api/auth/login", json={"email": "student@campusos.edu", "password": "campus123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    listing = client.post(
        "/api/listings",
        json={
            "title": f"Used textbook {uuid.uuid4().hex[:4]}",
            "description": "A used textbook in good condition for first-year students.",
            "category": "Books",
            "condition": "Good",
            "price": 500,
        },
        headers=student_headers,
    )
    listing_id = listing.json()["id"]
    other_email = f"other{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/auth/register", json={"email": other_email, "password": "campus123", "full_name": "Other Student"})
    other_login = client.post("/api/auth/login", json={"email": other_email, "password": "campus123"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    forbidden = client.patch(
        f"/api/listings/{listing_id}",
        json={"price": 1},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    report = client.post(
        f"/api/listings/{listing_id}/report",
        json={"reason": "The listing appears to include a prohibited product."},
        headers=other_headers,
    )
    assert report.status_code == 200
    staff_login = client.post("/api/auth/login", json={"email": "staff@campusos.edu", "password": "campus123"})
    staff_headers = {"Authorization": f"Bearer {staff_login.json()['access_token']}"}
    reports = client.get("/api/admin/listing-reports", headers=staff_headers)
    assert any(item["id"] == report.json()["report_id"] for item in reports.json())
    moderated = client.post(
        f"/api/admin/listing-reports/{report.json()['report_id']}/moderate?action=dismiss",
        headers=staff_headers,
    )
    assert moderated.status_code == 200


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
