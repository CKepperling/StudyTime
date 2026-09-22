import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.user import User

client = TestClient(app)

# Not a real, complete PDF - just enough of the standard header for
# our endpoint to accept, since it only checks content-type and size,
# not that the bytes actually parse as a valid document (that's T18's
# job, when text extraction gets built).
FAKE_PDF_BYTES = b"%PDF-1.4\n%fake pdf content for tests\n"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def _create_user_and_token(client: TestClient) -> tuple[str, str]:
    """Signs up a fresh user and returns (email, access_token)."""
    email = unique_email()
    password = "TestPassword123!"

    client.post("/auth/signup", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    return email, token


@pytest.fixture
def auth_headers():
    """A ready-to-use Authorization header for a fresh, unique user.

    Cleans up both the user and any documents they created, same
    spirit as test_auth.py's test_credentials fixture - tests
    shouldn't leave rows behind for the next run to trip over.
    """
    email, token = _create_user_and_token(client)

    yield {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        db.query(Document).filter(Document.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    db.close()


def test_upload_requires_auth():
    response = client.post(
        "/documents",
        files={"file": ("notes.pdf", FAKE_PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 401


def test_upload_rejects_non_pdf(auth_headers):
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"just some text", "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_upload_rejects_empty_file(auth_headers):
    response = client.post(
        "/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_upload_success(auth_headers):
    response = client.post(
        "/documents",
        files={"file": ("lecture-notes.pdf", FAKE_PDF_BYTES, "application/pdf")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "lecture-notes.pdf"
    assert body["status"] == "pending"
    assert "id" in body
    assert "created_at" in body
    # storage_path is internal - never returned to the client.
    assert "storage_path" not in body


def test_list_documents_requires_auth():
    response = client.get("/documents")

    assert response.status_code == 401


def test_list_documents_only_returns_own(auth_headers):
    # A second, separate user who also uploads a document - auth_headers'
    # fixture only cleans up ITS OWN user, so this one is torn down here.
    other_email, other_token = _create_user_and_token(client)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    try:
        client.post(
            "/documents",
            files={"file": ("someone-elses.pdf", FAKE_PDF_BYTES, "application/pdf")},
            headers=other_headers,
        )

        client.post(
            "/documents",
            files={"file": ("mine.pdf", FAKE_PDF_BYTES, "application/pdf")},
            headers=auth_headers,
        )

        response = client.get("/documents", headers=auth_headers)

        assert response.status_code == 200
        filenames = [doc["filename"] for doc in response.json()]
        assert "mine.pdf" in filenames
        assert "someone-elses.pdf" not in filenames
    finally:
        db = SessionLocal()
        other_user = db.query(User).filter(User.email == other_email).first()
        if other_user is not None:
            db.query(Document).filter(Document.user_id == other_user.id).delete()
            db.query(User).filter(User.id == other_user.id).delete()
            db.commit()
        db.close()


def test_list_documents_empty_for_new_user(auth_headers):
    response = client.get("/documents", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []
