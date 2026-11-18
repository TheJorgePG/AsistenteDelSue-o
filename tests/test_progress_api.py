from datetime import datetime, timedelta
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app


client = TestClient(app)


def register_and_login() -> tuple[str, str]:
    email = f"{uuid4().hex}@example.com"
    password = "test-password-123"
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert registration.status_code == 200
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return email, response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_profile_and_sleep_records_are_private_to_the_logged_in_user():
    _, first_token = register_and_login()
    _, second_token = register_and_login()
    first_headers = auth_header(first_token)
    second_headers = auth_header(second_token)
    profile_payload = {
        "display_name": "Alex",
        "age_range": "26-64",
        "sleep_goal_hours": 8,
        "timezone": "Europe/Madrid",
    }

    anonymous = client.get("/api/v1/profile")
    saved_profile = client.put(
        "/api/v1/profile",
        json=profile_payload,
        headers=first_headers,
    )
    first_profile = client.get("/api/v1/profile", headers=first_headers)
    second_profile = client.get("/api/v1/profile", headers=second_headers)
    unauthenticated_log = client.get("/api/v1/progress")
    second_progress = client.get("/api/v1/progress", headers=second_headers)
    today = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    created_log = client.post(
        "/api/v1/sleep-logs",
        headers=first_headers,
        json={
            "sleep_date": today,
            "hours_slept": 7,
            "quality_score": 7,
            "awakenings": 0,
        },
    )
    second_progress_after_log = client.get(
        "/api/v1/progress", headers=second_headers
    )

    assert anonymous.status_code == 401
    assert saved_profile.status_code == 200
    assert first_profile.json()["profile"]["display_name"] == "Alex"
    assert second_profile.json()["profile"] is None
    assert unauthenticated_log.status_code == 401
    assert created_log.status_code == 201
    assert second_progress.json()["sleep_logs"] == []
    assert second_progress_after_log.json()["sleep_logs"] == []


def test_sleep_log_awards_points_and_rejects_duplicate_day():
    _, token = register_and_login()
    headers = auth_header(token)
    sleep_date = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()
    payload = {
        "sleep_date": sleep_date,
        "hours_slept": 7.5,
        "quality_score": 8,
        "awakenings": 1,
    }

    created = client.post("/api/v1/sleep-logs", json=payload, headers=headers)
    duplicate = client.post("/api/v1/sleep-logs", json=payload, headers=headers)
    progress = client.get("/api/v1/progress", headers=headers).json()
    first_badge = next(
        badge for badge in progress["gamification"]["badges"]
        if badge["id"] == "first-night"
    )

    assert created.status_code == 201
    assert created.json()["sleep_log"]["hours_slept"] == 7.5
    assert duplicate.status_code == 409
    assert progress["gamification"]["points"] == 10
    assert progress["gamification"]["nights_logged"] == 1
    assert first_badge["unlocked"] is True


def test_seven_consecutive_logs_unlock_streak_badge():
    _, token = register_and_login()
    headers = auth_header(token)
    today = datetime.now(ZoneInfo("UTC")).date()

    for offset in range(7):
        response = client.post(
            "/api/v1/sleep-logs",
            headers=headers,
            json={
                "sleep_date": (today - timedelta(days=offset)).isoformat(),
                "hours_slept": 7,
                "quality_score": 7,
                "awakenings": 0,
            },
        )
        assert response.status_code == 201

    progress = client.get("/api/v1/progress", headers=headers).json()
    badge = next(
        item for item in progress["gamification"]["badges"]
        if item["id"] == "week-streak"
    )

    assert progress["gamification"]["points"] == 70
    assert progress["gamification"]["current_streak"] == 7
    assert badge["unlocked"] is True


def test_profile_validates_timezone_and_sleep_log_values():
    _, token = register_and_login()
    headers = auth_header(token)
    invalid_profile = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "display_name": "Alex",
            "age_range": "26-64",
            "sleep_goal_hours": 8,
            "timezone": "not-a-timezone",
        },
    )
    invalid_log = client.post(
        "/api/v1/sleep-logs",
        headers=headers,
        json={
            "sleep_date": datetime.now(ZoneInfo("UTC")).date().isoformat(),
            "hours_slept": 30,
            "quality_score": 8,
            "awakenings": 1,
        },
    )

    assert invalid_profile.status_code == 422
    assert invalid_log.status_code == 422


def test_progress_pdf_contains_profile_chart_and_history():
    _, token = register_and_login()
    headers = auth_header(token)
    sleep_date = datetime.now(ZoneInfo("UTC")).date().isoformat()
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "display_name": "Sam",
            "age_range": "18-25",
            "sleep_goal_hours": 8,
            "timezone": "UTC",
        },
    )
    client.post(
        "/api/v1/sleep-logs",
        headers=headers,
        json={
            "sleep_date": sleep_date,
            "hours_slept": 7,
            "quality_score": 7,
            "awakenings": 0,
        },
    )

    anonymous_response = client.get("/api/v1/reports/progress.pdf")
    response = client.get("/api/v1/reports/progress.pdf", headers=headers)
    pdf_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(BytesIO(response.content)).pages
    )

    assert anonymous_response.status_code == 401
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "Sam" in pdf_text
    assert "Calidad percibida" in pdf_text
    assert "Historial de sueño" in pdf_text
