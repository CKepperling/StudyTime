import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.note import Note
from app.models.user import User

client = TestClient(app)

FAKE_PDF_BYTES = b"%PDF-1.4\n%fake pdf content for tests\n"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def _create_user_and_token(client: TestClient) -> tuple[str, str]:
    email = unique_email()
    password = "TestPassword123!"

    client.post("/auth/signup", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    return email, token


def _cleanup_user(email: str) -> None:
    """Deletes a user and everything hanging off their documents -
    notes first, since Note has a foreign key to Document and most
    DBs won't let you delete a row something else still points at.
    """
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        document_ids = [
            d.id for d in db.query(Document).filter(Document.user_id == user.id).all()
        ]
        if document_ids:
            db.query(Note).filter(Note.document_id.in_(document_ids)).delete(
                synchronize_session=False
            )
        db.query(Document).filter(Document.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    db.close()


@pytest.fixture
def user_with_document():
    """A fresh user, their auth headers, and one document already
    uploaded for them - everything most note tests need to start from,
    bundled into one fixture so each test isn't repeating the same
    three setup calls. Cleans up notes, the document, and the user
    afterward regardless of whether the test passed.
    """
    email, token = _create_user_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/documents",
        files={"file": ("notes-source.pdf", FAKE_PDF_BYTES, "application/pdf")},
        headers=headers,
    )
    document_id = upload.json()["id"]

    yield {"headers": headers, "document_id": document_id}

    _cleanup_user(email)


# --- auth required ---


def test_list_notes_requires_auth(user_with_document):
    document_id = user_with_document["document_id"]
    response = client.get(f"/documents/{document_id}/notes")
    assert response.status_code == 401


def test_create_note_requires_auth(user_with_document):
    document_id = user_with_document["document_id"]
    response = client.post(f"/documents/{document_id}/notes", json={"content": "hi"})
    assert response.status_code == 401


# --- create + list ---


def test_create_and_list_note(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    create = client.post(
        f"/documents/{document_id}/notes",
        json={"content": "Glycolysis happens in the cytoplasm."},
        headers=headers,
    )
    assert create.status_code == 201
    body = create.json()
    assert body["content"] == "Glycolysis happens in the cytoplasm."
    assert body["document_id"] == document_id
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body

    listed = client.get(f"/documents/{document_id}/notes", headers=headers)
    assert listed.status_code == 200
    contents = [n["content"] for n in listed.json()]
    assert "Glycolysis happens in the cytoplasm." in contents


def test_list_notes_empty_for_new_document(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    response = client.get(f"/documents/{document_id}/notes", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_note_for_nonexistent_document_404(user_with_document):
    headers = user_with_document["headers"]
    response = client.post(
        "/documents/999999999/notes",
        json={"content": "hi"},
        headers=headers,
    )
    assert response.status_code == 404


# --- cross-user isolation ---


def test_create_note_for_other_users_document_404(user_with_document):
    other_email, other_token = _create_user_and_token(client)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    try:
        document_id = user_with_document["document_id"]  # belongs to the FIRST user

        # Second user tries to add a note to the first user's document.
        response = client.post(
            f"/documents/{document_id}/notes",
            json={"content": "sneaky note"},
            headers=other_headers,
        )
        assert response.status_code == 404
    finally:
        _cleanup_user(other_email)


def test_list_notes_for_other_users_document_404(user_with_document):
    other_email, other_token = _create_user_and_token(client)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    try:
        document_id = user_with_document["document_id"]
        response = client.get(f"/documents/{document_id}/notes", headers=other_headers)
        assert response.status_code == 404
    finally:
        _cleanup_user(other_email)


# --- update ---


def test_update_note(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    create = client.post(
        f"/documents/{document_id}/notes",
        json={"content": "original"},
        headers=headers,
    )
    note_id = create.json()["id"]

    update = client.put(
        f"/notes/{note_id}",
        json={"content": "edited"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["content"] == "edited"


def test_update_nonexistent_note_404(user_with_document):
    headers = user_with_document["headers"]
    response = client.put(
        "/notes/999999999",
        json={"content": "edited"},
        headers=headers,
    )
    assert response.status_code == 404


def test_update_other_users_note_404(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    create = client.post(
        f"/documents/{document_id}/notes",
        json={"content": "original"},
        headers=headers,
    )
    note_id = create.json()["id"]

    other_email, other_token = _create_user_and_token(client)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    try:
        response = client.put(
            f"/notes/{note_id}",
            json={"content": "hijacked"},
            headers=other_headers,
        )
        assert response.status_code == 404
    finally:
        _cleanup_user(other_email)


# --- delete ---


def test_delete_note(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    create = client.post(
        f"/documents/{document_id}/notes",
        json={"content": "to be deleted"},
        headers=headers,
    )
    note_id = create.json()["id"]

    delete = client.delete(f"/notes/{note_id}", headers=headers)
    assert delete.status_code == 204

    listed = client.get(f"/documents/{document_id}/notes", headers=headers)
    ids = [n["id"] for n in listed.json()]
    assert note_id not in ids


def test_delete_other_users_note_404(user_with_document):
    headers = user_with_document["headers"]
    document_id = user_with_document["document_id"]

    create = client.post(
        f"/documents/{document_id}/notes",
        json={"content": "protected"},
        headers=headers,
    )
    note_id = create.json()["id"]

    other_email, other_token = _create_user_and_token(client)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    try:
        response = client.delete(f"/notes/{note_id}", headers=other_headers)
        assert response.status_code == 404
    finally:
        _cleanup_user(other_email)