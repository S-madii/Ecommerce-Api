import httpx
import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_signup_and_duplicate_email(client: httpx.AsyncClient):
    response = await client.post(
        "/auth/signup",
        json={"email": "Alice@Example.com", "password": "Password123!"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"
    assert response.json()["role"] == "customer"
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
    assert "refresh_token" in body
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
async def test_me_refresh_and_logout_revocation(client: httpx.AsyncClient):
    await client.post(
        "/auth/signup",
        json={"email": "charlie@example.com", "password": "Password123!"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "charlie@example.com", "password": "Password123!"},
    )
    tokens = login_resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    me_resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "charlie@example.com"

    refresh_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_access_token = refresh_resp.json()["access_token"]

    reused_refresh = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused_refresh.status_code == 401

    logout_resp = await client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logout_resp.status_code == 200

    revoked_me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert revoked_me.status_code == 401


@pytest.mark.asyncio
async def test_auth_rate_limiting_and_admin_user_management(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "boss@example.com")

    admin_signup = await client.post(
        "/auth/signup",
        json={"email": "boss@example.com", "password": "Password123!"},
    )
    assert admin_signup.status_code == 201
    assert admin_signup.json()["role"] == "admin"

    admin_login = await client.post(
        "/auth/login",
        json={"email": "boss@example.com", "password": "Password123!"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    user_signup = await client.post(
        "/auth/signup",
        json={"email": "member@example.com", "password": "Password123!"},
    )
    member_id = user_signup.json()["id"]

    # Customer forbidden to list users
    user_login = await client.post(
        "/auth/login",
        json={"email": "member@example.com", "password": "Password123!"},
    )
    cust_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
    forbidden_list = await client.get("/auth/users", headers=cust_headers)
    assert forbidden_list.status_code == 403

    # Admin lists users
    users_resp = await client.get("/auth/users", headers=admin_headers)
    assert users_resp.status_code == 200
    assert users_resp.json()["total"] >= 2
    emails = [u["email"] for u in users_resp.json()["items"]]
    assert "boss@example.com" in emails
    assert "member@example.com" in emails

    # Admin filter by role
    admins_only = await client.get("/auth/users", params={"role": "admin"}, headers=admin_headers)
    assert admins_only.status_code == 200
    assert all(u["role"] == "admin" for u in admins_only.json()["items"])

    role_resp = await client.patch(
        f"/auth/users/{member_id}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert role_resp.status_code == 200
    assert role_resp.json()["role"] == "admin"

    del_resp = await client.delete(
        f"/auth/users/{member_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 204

    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_PER_MINUTE", 2)
    r1 = await client.post("/auth/login", json={"email": "x@example.com", "password": "Password123!"})
    r2 = await client.post("/auth/login", json={"email": "x@example.com", "password": "Password123!"})
    assert r1.status_code == 429 or r2.status_code == 429
