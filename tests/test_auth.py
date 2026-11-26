import httpx
import pytest


@pytest.mark.asyncio
async def test_signup_and_duplicate_email(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/signup",
        json={"email": "Alice@Example.com", "password": "Password123!"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"
    assert "password" not in response.json()

    dup_response = await client.post(
        "/auth/signup",
        json={"email": "alice@example.com", "password": "Password123!"},
    )
    assert dup_response.status_code == 409


@pytest.mark.asyncio
async def test_login_success_and_wrong_password(client: httpx.AsyncClient):
    await client.post(
        "/auth/signup",
        json={"email": "bob@example.com", "password": "Password123!"},
    )

    login_resp = await client.post(
        "/auth/login",
        json={"email": "BOB@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"

    wrong_pw_resp = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "WrongPassword1!"},
    )
    assert wrong_pw_resp.status_code == 401

    ghost_resp = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Password123!"},
    )
    assert ghost_resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_auth_guard(client: httpx.AsyncClient):
    await client.post(
        "/auth/signup",
        json={"email": "charlie@example.com", "password": "Password123!"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "charlie@example.com", "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "charlie@example.com"

    bad_resp = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert bad_resp.status_code == 401
