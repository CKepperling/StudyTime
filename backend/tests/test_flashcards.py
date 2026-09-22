import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.review_log import ReviewLog
from app.models.user import User

client = TestClient(app)

TEST_PASSWORD = "TestPassword123!"


def now() -> datetime:
    # Naive UTC on purpose - matches Flashcard.due_at's own storage
    # format (see the comment in app/services/sm2.py).
    return datetime.utcnow()  # noqa: DTZ003


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


def _make_flashcard(document_id: int, due_at: datetime) -> int:
    db = SessionLocal()
    flashcard = Flashcard(
        document_id=document_id,
        front="What is spaced repetition?",
        back="A review technique that spaces reviews out over time.",
        source=FlashcardSource.AI_GENERATED,
        due_at=due_at,
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
        flashcard_ids = [
            f.id
            for f in db.query(Flashcard).filter(Flashcard.document_id.in_(doc_ids))
        ]
        if flashcard_ids:
            db.query(ReviewLog).filter(
                ReviewLog.flashcard_id.in_(flashcard_ids)
            ).delete(synchronize_session=False)
            db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).delete(
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


def test_due_flashcards_includes_overdue_card(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    _make_flashcard(document_id, due_at=now() - timedelta(days=1))

    response = client.get("/flashcards/due", headers=headers)

    assert response.status_code == 200
    cards = response.json()
    assert len(cards) == 1
    assert cards[0]["document_id"] == document_id


def test_due_flashcards_excludes_future_card(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    _make_flashcard(document_id, due_at=now() + timedelta(days=5))

    response = client.get("/flashcards/due", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_due_flashcards_excludes_other_users_cards(user_and_headers):
    _, headers = user_and_headers
    other_user_id, _token = _create_user_and_token()
    other_document_id = _make_document(other_user_id)
    _make_flashcard(other_document_id, due_at=now() - timedelta(days=1))

    response = client.get("/flashcards/due", headers=headers)

    assert response.status_code == 200
    assert response.json() == []

    _delete_user_and_their_data(other_user_id)


def test_submit_review_updates_scheduling_state(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    flashcard_id = _make_flashcard(document_id, due_at=now() - timedelta(days=1))

    response = client.post(
        f"/flashcards/{flashcard_id}/review", json={"grade": 2}, headers=headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["repetitions"] == 1
    assert body["interval_days"] == 1

    # The card should no longer show up as due immediately after a
    # passing review.
    due_response = client.get("/flashcards/due", headers=headers)
    assert due_response.json() == []


def test_submit_review_records_a_review_log(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    flashcard_id = _make_flashcard(document_id, due_at=now())

    client.post(
        f"/flashcards/{flashcard_id}/review", json={"grade": 3}, headers=headers
    )

    db = SessionLocal()
    logs = db.query(ReviewLog).filter(ReviewLog.flashcard_id == flashcard_id).all()
    assert len(logs) == 1
    assert logs[0].grade == 3
    db.close()


def test_submit_review_rejects_out_of_range_grade(user_and_headers):
    user_id, headers = user_and_headers
    document_id = _make_document(user_id)
    flashcard_id = _make_flashcard(document_id, due_at=now())

    response = client.post(
        f"/flashcards/{flashcard_id}/review", json={"grade": 7}, headers=headers
    )

    assert response.status_code == 422


def test_submit_review_404s_for_other_users_flashcard(user_and_headers):
    _, headers = user_and_headers
    other_user_id, _token = _create_user_and_token()
    other_document_id = _make_document(other_user_id)
    other_flashcard_id = _make_flashcard(other_document_id, due_at=now())

    response = client.post(
        f"/flashcards/{other_flashcard_id}/review", json={"grade": 2}, headers=headers
    )

    assert response.status_code == 404

    _delete_user_and_their_data(other_user_id)


def test_submit_review_404s_for_nonexistent_flashcard(user_and_headers):
    _, headers = user_and_headers

    response = client.post(
        "/flashcards/999999999/review", json={"grade": 2}, headers=headers
    )

    assert response.status_code == 404


def test_flashcards_require_auth():
    response = client.get("/flashcards/due")
    assert response.status_code == 401
