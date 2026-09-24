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
from app.services.progress import MASTERED_REPETITIONS, compute_progress_stats

client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def _make_user() -> int:
    db = SessionLocal()
    user = User(email=unique_email(), hashed_password="not-a-real-hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    return user_id


def _make_document(user_id: int) -> int:
    db = SessionLocal()
    document = Document(
        user_id=user_id,
        filename="lecture.pdf",
        storage_path=f"{uuid.uuid4().hex}.pdf",
        status="extracted",
    )
    db.add(document)
    db.commit()
    document_id = document.id
    db.close()
    return document_id


def _make_flashcard(
    document_id: int,
    *,
    due_at: datetime,
    repetitions: int = 0,
    source: FlashcardSource = FlashcardSource.AI_GENERATED,
) -> int:
    db = SessionLocal()
    flashcard = Flashcard(
        document_id=document_id,
        front="Q",
        back="A",
        source=source,
        repetitions=repetitions,
        due_at=due_at,
    )
    db.add(flashcard)
    db.commit()
    flashcard_id = flashcard.id
    db.close()
    return flashcard_id


def _make_review(flashcard_id: int, grade: int, reviewed_at: datetime) -> None:
    db = SessionLocal()
    db.add(ReviewLog(flashcard_id=flashcard_id, grade=grade, reviewed_at=reviewed_at))
    db.commit()
    db.close()


def _cleanup_user(user_id: int) -> None:
    db = SessionLocal()
    doc_ids = [d.id for d in db.query(Document).filter(Document.user_id == user_id)]
    if doc_ids:
        flashcard_ids = [
            f.id for f in db.query(Flashcard).filter(Flashcard.document_id.in_(doc_ids))
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
def user_id():
    uid = _make_user()
    yield uid
    _cleanup_user(uid)


NOW = datetime.utcnow()  # noqa: DTZ003


def _db():
    """A fresh session for a single compute_progress_stats call - kept
    separate from whatever session a test's _make_* helpers already
    used, so stats are read back through their own query rather than
    relying on another session's identity map.
    """
    return SessionLocal()


# ============================================================
# app/services/progress.py - compute_progress_stats
# ============================================================


def test_empty_user_gets_all_zeros(user_id):
    stats = compute_progress_stats(_db(), user_id)

    assert stats.total_documents == 0
    assert stats.total_flashcards == 0
    assert stats.flashcards_due_now == 0
    assert stats.cards_mastered == 0
    assert stats.reviews_today == 0
    assert stats.reviews_last_7_days == 0
    assert stats.accuracy_last_7_days is None
    assert stats.current_streak_days == 0


def test_counts_documents_and_flashcards(user_id):
    doc_id = _make_document(user_id)
    _make_flashcard(doc_id, due_at=NOW)
    _make_flashcard(doc_id, due_at=NOW)

    stats = compute_progress_stats(_db(), user_id)

    assert stats.total_documents == 1
    assert stats.total_flashcards == 2


def test_does_not_count_other_users_data(user_id):
    other_user_id = _make_user()
    try:
        other_doc = _make_document(other_user_id)
        _make_flashcard(other_doc, due_at=NOW)

        stats = compute_progress_stats(_db(), user_id)

        assert stats.total_documents == 0
        assert stats.total_flashcards == 0
    finally:
        _cleanup_user(other_user_id)


def test_flashcards_due_now_excludes_future_cards(user_id):
    doc_id = _make_document(user_id)
    _make_flashcard(doc_id, due_at=NOW - timedelta(days=1))  # due
    _make_flashcard(doc_id, due_at=NOW + timedelta(days=5))  # not due yet

    stats = compute_progress_stats(_db(), user_id)

    assert stats.flashcards_due_now == 1


def test_cards_mastered_uses_repetitions_threshold(user_id):
    doc_id = _make_document(user_id)
    _make_flashcard(doc_id, due_at=NOW, repetitions=MASTERED_REPETITIONS)
    _make_flashcard(doc_id, due_at=NOW, repetitions=MASTERED_REPETITIONS + 5)
    _make_flashcard(doc_id, due_at=NOW, repetitions=MASTERED_REPETITIONS - 1)

    stats = compute_progress_stats(_db(), user_id)

    assert stats.cards_mastered == 2


def test_reviews_today_excludes_earlier_days(user_id):
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)

    _make_review(card_id, grade=2, reviewed_at=NOW)
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=1, hours=1))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.reviews_today == 1


def test_reviews_last_7_days_and_accuracy(user_id):
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)

    # 3 passing (grade >= 1), 1 failing (grade 0), all within the window
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=1))
    _make_review(card_id, grade=3, reviewed_at=NOW - timedelta(days=2))
    _make_review(card_id, grade=1, reviewed_at=NOW - timedelta(days=3))
    _make_review(card_id, grade=0, reviewed_at=NOW - timedelta(days=4))
    # Outside the 7-day window - must not count
    _make_review(card_id, grade=3, reviewed_at=NOW - timedelta(days=10))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.reviews_last_7_days == 4
    assert stats.accuracy_last_7_days == 75.0


def test_accuracy_is_none_with_no_recent_reviews(user_id):
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)
    _make_review(card_id, grade=3, reviewed_at=NOW - timedelta(days=30))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.reviews_last_7_days == 0
    assert stats.accuracy_last_7_days is None


def test_streak_counts_consecutive_days_including_today(user_id):
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)

    _make_review(card_id, grade=2, reviewed_at=NOW)
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=1))
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=2))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.current_streak_days == 3


def test_streak_still_counts_if_not_reviewed_yet_today(user_id):
    """Reviewed yesterday and the day before, nothing yet today - the
    streak should still show as alive (2), not reset to 0, since today
    isn't over yet.
    """
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)

    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=1))
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=2))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.current_streak_days == 2


def test_streak_breaks_on_a_gap(user_id):
    doc_id = _make_document(user_id)
    card_id = _make_flashcard(doc_id, due_at=NOW)

    _make_review(card_id, grade=2, reviewed_at=NOW)
    # Skips yesterday entirely
    _make_review(card_id, grade=2, reviewed_at=NOW - timedelta(days=2))

    stats = compute_progress_stats(_db(), user_id)

    assert stats.current_streak_days == 1


def test_streak_zero_with_no_reviews_at_all(user_id):
    doc_id = _make_document(user_id)
    _make_flashcard(doc_id, due_at=NOW)

    stats = compute_progress_stats(_db(), user_id)

    assert stats.current_streak_days == 0


# ============================================================
# GET /progress
# ============================================================


def _signup_and_login(email: str, password: str = "TestPassword123!") -> str:
    client.post("/auth/signup", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_get_progress_requires_auth():
    response = client.get("/progress")

    assert response.status_code == 401


def test_get_progress_returns_stats_for_current_user():
    email = unique_email()
    token = _signup_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user_id_local = user.id
    db.close()

    doc_id = _make_document(user_id_local)
    _make_flashcard(doc_id, due_at=NOW - timedelta(hours=1))

    try:
        response = client.get("/progress", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total_documents"] == 1
        assert body["total_flashcards"] == 1
        assert body["flashcards_due_now"] == 1
        assert body["accuracy_last_7_days"] is None
    finally:
        _cleanup_user(user_id_local)
