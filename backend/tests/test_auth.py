import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)


def unique_email() -> str:
    # A fresh random email per test avoids colliding with rows already
    # in the real dev DB from manual /docs testing, and with each other
    # if tests run more than once.
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_credentials():
    """Provides a fresh email/password pair, and deletes that user
    from the DB after the test finishes - runs regardless of whether
    the test passed or failed, so leftover test users don't pile up.
    """
    email = unique_email()
    password = "TestPassword123!"

    yield {"email": email, "password": password}

    db = SessionLocal()
    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()


def test_signup_success(test_credentials):
    response = client.post("/auth/signup", json=test_credentials)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == test_credentials["email"]
    assert "id" in body
    # The real check: hashed_password must NEVER appear in the response,
    # confirming UserOut's response_model actually strips it.
    assert "hashed_password" not in body
    assert "password" not in body


def test_signup_duplicate_email_rejected(test_credentials):
    # First signup should succeed...
    first = client.post("/auth/signup", json=test_credentials)
    assert first.status_code == 201

    # ...second signup with the SAME email should be rejected, not
    # silently create a second account or overwrite the first.
    second = client.post("/auth/signup", json=test_credentials)
    assert second.status_code == 400


def test_login_success(test_credentials):
    client.post("/auth/signup", json=test_credentials)

    response = client.post("/auth/login", json=test_credentials)

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_rejected(test_credentials):
    client.post("/auth/signup", json=test_credentials)

    wrong_login = {"email": test_credentials["email"], "password": "WrongPassword!"}
    response = client.post("/auth/login", json=wrong_login)

    assert response.status_code == 401


def test_login_nonexistent_user_rejected():
    response = client.post(
        "/auth/login",
        json={"email": "nobody-real@example.com", "password": "whatever"},
    )

    assert response.status_code == 401


def test_me_requires_auth():
    # No Authorization header at all - should be rejected before it
    # ever looks at a database.
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_rejects_garbage_token():
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_me_returns_current_user(test_credentials):
    client.post("/auth/signup", json=test_credentials)
    login_response = client.post("/auth/login", json=test_credentials)
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == test_credentials["email"]
    assert "hashed_password" not in body