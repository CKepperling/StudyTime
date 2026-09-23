import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.user import User

client = TestClient(app)

TEST_PASSWORD = "TestPassword123!"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def _create_user_and_token() -> tuple[int, str]:
    email = unique_email()
    client.post("/auth/signup", json={"email": email, "password": TEST_PASSWORD})
    login = client.post(
        "/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    token = login.json()["access_token"]

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user_id = user.id
    db.close()

    return user_id, token


def _make_document(user_id: int) -> int:
    db = SessionLocal()
    document = Document(
        user_id=user_id,
        filename="test.pdf",
        storage_path=f"{uuid.uuid4().hex}.pdf",
        status="extracted",
    )
    db.add(document)
    db.commit()
    document_id = document.id
    db.close()
    return document_id


def _make_flashcard(document_id: int, front: str, back: str) -> int:
    db = SessionLocal()
    flashcard = Flashcard(
        document_id=document_id,
        front=front,
        back=back,
        source=FlashcardSource.AI_GENERATED,
        due_at=datetime.utcnow(),  # noqa: DTZ003
    )
    db.add(flashcard)
    db.commit()
    flashcard_id = flashcard.id
    db.close()
    return flashcard_id


def _delete_user_and_their_data(user_id: int) -> None:
    db = SessionLocal()
    doc_ids = [d.id for d in db.query(Document).filter(Document.user_id == user_id)]
    if doc_ids:
        db.query(Flashcard).filter(Flashcard.document_id.in_(doc_ids)).delete(
            synchronize_session=False
        )
        db.query(Document).filter(Document.id.in_(doc_ids)).delete(
            synchronize_session=False
        )
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


@pytest.fixture
def user_and_headers():
    user_id, token = _create_user_and_token()
    headers = {"Authorization": f"Bearer {token}"}

    yield user_id, headers

    _delete_user_and_their_data(user_id)


def test_list_flashcards_returns_cards_for_document(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    _make_flashcard(document_id, "Q1", "A1")
    _make_flashcard(document_id, "Q2", "A2")

    response = client.get(f"/documents/{document_id}/flashcards", headers=headers)

    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 2
    assert {c["front"] for c in cards} == {"Q1", "Q2"}


def test_list_flashcards_empty_for_document_with_none(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)

    response = client.get(f"/documents/{document_id}/flashcards", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_flashcards_404s_for_other_users_document(user_and_headers):
    _, headers = user_and_headers
    other_user_id, _token = _create_user_and_token()
    other_document_id = _make_document(other_user_id)
    _make_flashcard(other_document_id, "Q1", "A1")

    response = client.get(
        f"/documents/{other_document_id}/flashcards", headers=headers
    )

    assert response.status_code == 404

    _delete_user_and_their_data(other_user_id)


def test_list_flashcards_404s_for_nonexistent_document(user_and_headers):
    _, headers = user_and_headers

    response = client.get("/documents/999999999/flashcards", headers=headers)

    assert response.status_code == 404


def test_list_flashcards_requires_auth(user_and_headers):
    user_id, _headers = user_and_headers
    document_id = _make_document(user_id)

    response = client.get(f"/documents/{document_id}/flashcards")

    assert response.status_code == 401


# ============================================================
# POST /documents/{id}/flashcards - manual creation
# ============================================================


def test_create_manual_flashcard_returns_created_card(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)

    response = client.post(
        f"/documents/{document_id}/flashcards",
        json={"front": "What is SM-2?", "back": "A spaced-repetition algorithm."},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["front"] == "What is SM-2?"
    assert body["back"] == "A spaced-repetition algorithm."
    assert body["source"] == "manual"
    # New manual cards get the same default scheduling state as any
    # other flashcard - due immediately, at the standard starting ease.
    assert body["repetitions"] == 0
    assert body["ease_factor"] == 2.5


def test_create_manual_flashcard_persists_to_document(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)

    client.post(
        f"/documents/{document_id}/flashcards",
        json={"front": "Q", "back": "A"},
        headers=headers,
    )

    response = client.get(f"/documents/{document_id}/flashcards", headers=headers)
    cards = response.json()
    assert len(cards) == 1
    assert cards[0]["source"] == "manual"


def test_create_manual_flashcard_404s_for_other_users_document(user_and_headers):
    _, headers = user_and_headers
    other_user_id, _token = _create_user_and_token()
    other_document_id = _make_document(other_user_id)

    response = client.post(
        f"/documents/{other_document_id}/flashcards",
        json={"front": "Q", "back": "A"},
        headers=headers,
    )

    assert response.status_code == 404

    _delete_user_and_their_data(other_user_id)


def test_create_manual_flashcard_rejects_empty_front(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)

    response = client.post(
        f"/documents/{document_id}/flashcards",
        json={"front": "", "back": "A"},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_manual_flashcard_requires_auth(user_and_headers):
    user_id, _headers = user_and_headers
    document_id = _make_document(user_id)

    response = client.post(
        f"/documents/{document_id}/flashcards",
        json={"front": "Q", "back": "A"},
    )

    assert response.status_code == 401
