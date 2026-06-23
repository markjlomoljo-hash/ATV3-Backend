"""
End-to-end pipeline tests: product analysis -> health index -> forecast.
These cover the real formula implementations and confirm the service layer
wires together correctly (not just that individual units return a value).
"""
import uuid
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio


async def _authenticated_headers(client) -> dict:
    email = f"e2e_{uuid.uuid4().hex[:12]}@example.com"
    resp = await client.post("/v1/auth/signup", json={"email": email, "password": "CorrectHorse9battery", "display_name": "E2E User"})
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_product_analysis_returns_real_scores_not_fabricated(client):
    headers = await _authenticated_headers(client)
    resp = await client.post("/v1/products/analyze", headers=headers, json={
        "product_name": "Test Moisturizer",
        "brand": "TestBrand",
        "input_method": "manual",
        # Coconut oil (comedo 4) + niacinamide (comedo 0) = avg 2.0
        "raw_ingredient_text": "Water, Coconut Oil, Niacinamide, Glycerin, Fragrance",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["comedogenic_score"] == 2.0, "avg comedogenic should be (4+0)/2 = 2.0 from real IngredientProfile rows"
    assert data["conclusion"] is not None and len(data["conclusion"]) > 10
    assert data["confidence_level"] in ("low", "moderate", "high")
    # Must never be a fabricated flat number
    assert data["overall_risk"] != 50, "50 is the empty-ingredient fallback - real ingredients should produce a distinct number"


async def test_health_index_reflects_zero_data_honestly(client):
    headers = await _authenticated_headers(client)
    resp = await client.get("/v1/health-index/latest", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # A brand-new account with zero logs should not claim high confidence
    assert data["data_density"] in ("low", "moderate"), "new account should be 'low' or 'moderate' data density, not 'very_high'"
    # validation_status should be honest about insufficient data
    assert data["validation_status"] in ("insufficient_data", "passed")


async def test_forecast_refuses_without_enough_data(client):
    headers = await _authenticated_headers(client)
    resp = await client.post("/v1/forecast", headers=headers, json={"horizon_days": 7})
    # Should be 422 insufficient_data, not a fabricated forecast
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "insufficient_data", "forecast must refuse to fabricate a result without real history"


async def test_forecast_succeeds_after_real_logs(client):
    headers = await _authenticated_headers(client)
    # Submit 7 days of real logs across sleep + food + stress
    for i in range(7):
        day = (date.today() - timedelta(days=i)).isoformat()
        await client.post("/v1/logs/sleep", headers=headers, json={
            "log_date": day, "bedtime": "23:00", "wake_time": "07:00", "quality": 6,
            "fragmented": False, "late_night_shift": False,
        })
        await client.post("/v1/logs/food", headers=headers, json={
            "log_date": day, "meals": [], "hydration_liters": 2.0,
            "glycemic_load": 45, "dairy_intake": True, "whey_protein": False,
            "sugar_load": "moderate", "processed_food_level": "minimal",
        })

    resp = await client.post("/v1/forecast", headers=headers, json={"horizon_days": 7})
    assert resp.status_code == 200
    data = resp.json()
    assert 5 <= data["forecasted_risk"] <= 95, "risk should be clamped to the real [5, 95] range"
    assert data["validation_status"] == "passed"
    assert len(data["recommendations"]) > 0
    assert data["key_drivers"] is not None


async def test_what_if_requires_existing_forecast(client):
    headers = await _authenticated_headers(client)
    resp = await client.post("/v1/what-if", headers=headers, json={
        "changed_factors": [{"factor": "Poor Sleep Quality", "direction": "improve", "magnitude": 70}],
    })
    # Should fail clearly rather than fabricate a what-if with no baseline
    assert resp.status_code in (404, 422)


async def test_assistant_conversation_full_flow(client):
    headers = await _authenticated_headers(client)

    # Create conversation
    conv_resp = await client.post("/v1/assistant/conversations", headers=headers, json={"title": "Test convo"})
    assert conv_resp.status_code == 200
    conv_id = conv_resp.json()["id"]

    # List conversations should return the new one
    list_resp = await client.get("/v1/assistant/conversations", headers=headers)
    assert list_resp.status_code == 200
    assert any(c["id"] == conv_id for c in list_resp.json())

    # Post a message - will return 501 if ANTHROPIC_API_KEY is not set (correct behavior)
    msg_resp = await client.post(
        f"/v1/assistant/conversations/{conv_id}/messages",
        headers=headers, json={"content": "What does my barrier integrity score mean?"},
    )
    # 200 with real key, 501 without - both are correct, neither is a fabricated 200
    assert msg_resp.status_code in (200, 501)
    if msg_resp.status_code == 501:
        assert msg_resp.json()["error"] == "not_implemented_yet"


async def test_evidence_search_returns_real_rows(client):
    headers = await _authenticated_headers(client)
    resp = await client.get("/v1/evidence/search?q=acne+sleep", headers=headers)
    assert resp.status_code == 200
    # After seed, this should return at least the Jovic et al. sleep/acne paper
    # (only available if seed has been run against the test DB)
    results = resp.json()
    assert isinstance(results, list)
    # We can't assert count > 0 without knowing if seed ran, but we can
    # assert the shape of whatever comes back
    for r in results:
        assert "title" in r
        assert "abstract_summary" in r
        assert "source_url" in r
