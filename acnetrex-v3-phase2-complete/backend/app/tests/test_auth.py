import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


async def test_signup_then_login_with_same_credentials_succeeds(client):
    email = await _unique_email()
    password = "CorrectHorse9battery"

    signup_resp = await client.post("/v1/auth/signup", json={"email": email, "password": password, "display_name": "Test User"})
    assert signup_resp.status_code == 201
    body = signup_resp.json()
    assert body["user"]["email"] == email
    assert body["access_token"]

    login_resp = await client.post("/v1/auth/login", json={"email": email, "password": password, "remember_me": False})
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["email"] == email


async def test_duplicate_signup_rejected(client):
    email = await _unique_email()
    password = "CorrectHorse9battery"
    first = await client.post("/v1/auth/signup", json={"email": email, "password": password, "display_name": "First"})
    assert first.status_code == 201

    second = await client.post("/v1/auth/signup", json={"email": email, "password": password, "display_name": "Second"})
    assert second.status_code == 409
    assert second.json()["error"] == "account_exists"


async def test_login_with_wrong_password_rejected(client):
    email = await _unique_email()
    password = "CorrectHorse9battery"
    await client.post("/v1/auth/signup", json={"email": email, "password": password, "display_name": "Test"})

    bad_login = await client.post("/v1/auth/login", json={"email": email, "password": "totally-wrong-password", "remember_me": False})
    assert bad_login.status_code == 401
    assert bad_login.json()["error"] == "invalid_credentials"


async def test_me_requires_valid_token(client):
    no_token = await client.get("/v1/auth/me")
    assert no_token.status_code in (401, 403)  # FastAPI's HTTPBearer returns 403 when the header is entirely missing

    bad_token = await client.get("/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert bad_token.status_code == 401


async def test_logout_revokes_session_immediately(client):
    email = await _unique_email()
    password = "CorrectHorse9battery"
    signup_resp = await client.post("/v1/auth/signup", json={"email": email, "password": password, "display_name": "Test"})
    token = signup_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    still_valid = await client.get("/v1/auth/me", headers=headers)
    assert still_valid.status_code == 200

    logout_resp = await client.post("/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 204

    # Same token, now dead - this is the server-side revocation working,
    # not just a client deleting a local token.
    after_logout = await client.get("/v1/auth/me", headers=headers)
    assert after_logout.status_code == 401
