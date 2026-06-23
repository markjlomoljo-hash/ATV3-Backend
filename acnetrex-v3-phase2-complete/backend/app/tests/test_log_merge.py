import uuid
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio


async def _signed_up_headers(client) -> dict:
    email = f"test_{uuid.uuid4().hex[:12]}@example.com"
    resp = await client.post("/v1/auth/signup", json={"email": email, "password": "CorrectHorse9battery", "display_name": "Test"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_second_sleep_log_same_day_merges_not_duplicates(client):
    headers = await _signed_up_headers(client)
    today = date.today().isoformat()

    first = await client.post("/v1/logs/sleep", headers=headers, json={
        "log_date": today, "bedtime": "23:00", "wake_time": "06:30", "quality": 6, "fragmented": False, "late_night_shift": False,
    })
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["was_merged"] is False
    first_id = first_body["id"]

    second = await client.post("/v1/logs/sleep", headers=headers, json={
        "log_date": today, "bedtime": "23:30", "wake_time": "07:00", "quality": 8, "fragmented": True, "late_night_shift": False,
    })
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["was_merged"] is True
    assert second_body["id"] == first_id, "same-day log must update the existing row, not create a new one"
    assert second_body["data"]["quality"] == 8, "merged record should reflect the latest submission's values"

    today_logs = await client.get("/v1/logs/today", headers=headers)
    sleep_logs_today = [l for l in today_logs.json() if l["log_type"] == "sleep"]
    assert len(sleep_logs_today) == 1, "exactly one sleep log should exist for today, never two"


async def test_sleep_log_different_day_creates_separate_record(client):
    headers = await _signed_up_headers(client)
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    today_log = await client.post("/v1/logs/sleep", headers=headers, json={
        "log_date": today, "bedtime": "23:00", "wake_time": "06:30", "quality": 6, "fragmented": False, "late_night_shift": False,
    })
    yesterday_log = await client.post("/v1/logs/sleep", headers=headers, json={
        "log_date": yesterday, "bedtime": "22:00", "wake_time": "05:30", "quality": 7, "fragmented": False, "late_night_shift": False,
    })

    assert today_log.json()["was_merged"] is False
    assert yesterday_log.json()["was_merged"] is False
    assert today_log.json()["id"] != yesterday_log.json()["id"]


async def test_food_log_overall_risk_computed_server_side(client):
    headers = await _signed_up_headers(client)
    resp = await client.post("/v1/logs/food", headers=headers, json={
        "meals": [{"name": "Pizza"}], "hydration_liters": 1.5, "glycemic_load": 80,
        "dairy_intake": True, "whey_protein": False, "sugar_load": "high", "processed_food_level": "high",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    # 80*0.4 + 20 (dairy) + 0 (no whey) + 20 (sugar high) + 15 (processed high) = 87
    assert data["overallRisk"] == 87
    # Client cannot inject its own overallRisk - server computed it regardless of what was (not) sent.
    assert "overallRisk" in data
