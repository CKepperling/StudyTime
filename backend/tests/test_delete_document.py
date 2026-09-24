import uuid

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.note import Note
from app.models.practice_test import PracticeTest, TestQuestion
from app.models.review_log import ReviewLog
from app.models.summary import DifficultyLevel, Summary
from app.models.user import User
from app.storage import UPLOAD_DIR

client = TestClient(app)

TEST_PASSWORD = "TestPassword123!"


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def _create_user_and_token() -> tuple[int, str]:
    email = unique_email()
    client.post("/auth/signup", json={"email": email, "password": TEST_PASSWORD})
    login = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
    token = login.json()["access_token"]

    db = SessionLocal()
    user_id = db.query(User).filter(User.email == email).first().id
    db.close()

    return user_id, token


def _make_fully_populated_document(user_id: int) -> int:
    """A document with one row in every table that hangs off it -
    everything the cascade delete is supposed to clean up. Also writes
    a real file to UPLOAD_DIR matching storage_path, so the delete
    endpoint's disk cleanup has something real to remove.
    """
    db = SessionLocal()

    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(b"%PDF-1.4 fake content")

    document = Document(
        user_id=user_id,
        filename="everything.pdf",
        storage_path=storage_path,
        status="extracted",
        extracted_text="some text",
    )
    db.add(document)
    db.flush()

    summary = Summary(
        document_id=document.id,
        difficulty_level=DifficultyLevel.MEDIUM,
        content="a summary",
    )
    db.add(summary)

    note = Note(document_id=document.id, content="a note")
    db.add(note)

    flashcard = Flashcard(
        document_id=document.id,
        front="Q",
        back="A",
        source=FlashcardSource.MANUAL,
    )
    db.add(flashcard)
    db.flush()

    review_log = ReviewLog(flashcard_id=flashcard.id, grade=2)
    db.add(review_log)

    practice_test = PracticeTest(document_id=document.id)
    db.add(practice_test)
    db.flush()

    question = TestQuestion(
        practice_test_id=practice_test.id, question="Q", correct_answer="A"
    )
    db.add(question)

    db.commit()
    document_id = document.id
    db.close()
    return document_id


def _counts_for_document(document_id: int) -> dict:
    """Row counts across every table that should be emptied by the
    cascade - the actual assertion surface for these tests.
    """
    db = SessionLocal()
    counts = {
        "document": db.query(Document).filter(Document.id == document_id).count(),
        "summary": db.query(Summary).filter(Summary.document_id == document_id).count(),
        "note": db.query(Note).filter(Note.document_id == document_id).count(),
        "flashcard": db.query(Flashcard)
        .filter(Flashcard.document_id == document_id)
        .count(),
        "review_log": db.query(ReviewLog)
        .join(Flashcard, ReviewLog.flashcard_id == Flashcard.id)
        .filter(Flashcard.document_id == document_id)
        .count(),
        "practice_test": db.query(PracticeTest)
        .filter(PracticeTest.document_id == document_id)
        .count(),
        "test_question": db.query(TestQuestion)
        .join(PracticeTest, TestQuestion.practice_test_id == PracticeTest.id)
        .filter(PracticeTest.document_id == document_id)
        .count(),
    }
    db.close()
    return counts


def _delete_user(user_id: int) -> None:
    """Deletes a user, and any documents they still own first.

    Most tests in this file leave no document behind (the test itself
    deleted it), so this is a no-op in those cases. But the "other
    user's delete attempt gets rejected" test deliberately leaves the
    document alive to prove nothing was touched - Query.delete() alone
    on the user would then hit a foreign key violation, since there's
    no cascade from User to Document (only Document to ITS children).
    session.delete() on each surviving document (not the bulk
    Query.delete()) respects the ORM-level cascade, cleaning up
    everything that document owns too.
    """
    db = SessionLocal()
    remaining_documents = db.query(Document).filter(Document.user_id == user_id).all()
    for document in remaining_documents:
        # Only test_delete_document_404s_for_other_users_document ever
        # actually reaches this loop with a real document in it - that
        # test's whole point is a REJECTED delete attempt, so the app's
        # own file-cleanup code (in api/documents.py) never runs for it.
        # Without this, every run of that one test would leave one more
        # orphaned file behind in uploads/, forever.
        try:
            (UPLOAD_DIR / document.storage_path).unlink()
        except FileNotFoundError:
            pass
        db.delete(document)
    # This app's SessionLocal is configured with autoflush=False (see
    # app/db.py), so the db.delete(document) calls above are only
    # staged in Python until something actually flushes them - without
    # this line, the query below would run BEFORE those deletes ever
    # reach Postgres, and hit the exact same foreign key violation this
    # whole function exists to avoid.
    db.flush()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


def test_delete_document_requires_auth():
    response = client.delete("/documents/1")
    assert response.status_code == 401


def test_delete_document_404s_for_nonexistent_document():
    user_id, token = _create_user_and_token()
    try:
        response = client.delete(
            "/documents/999999999", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        _delete_user(user_id)


def test_delete_document_404s_for_other_users_document():
    owner_id, _owner_token = _create_user_and_token()
    other_id, other_token = _create_user_and_token()
    document_id = _make_fully_populated_document(owner_id)

    try:
        response = client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {other_token}"}
        )
        assert response.status_code == 404

        # Nothing should have been touched - this is the security-relevant
        # half of this test, not just the 404 status code.
        counts = _counts_for_document(document_id)
        assert counts["document"] == 1
    finally:
        _delete_user(owner_id)
        _delete_user(other_id)


def test_delete_document_removes_every_related_row():
    """The real point of this file: deleting a document with one row in
    every related table leaves NOTHING behind in any of them - this is
    what actually proves the cascade="all, delete-orphan" settings work,
    not just that the endpoint returns 204.
    """
    user_id, token = _create_user_and_token()
    document_id = _make_fully_populated_document(user_id)

    try:
        before = _counts_for_document(document_id)
        assert before == {
            "document": 1,
            "summary": 1,
            "note": 1,
            "flashcard": 1,
            "review_log": 1,
            "practice_test": 1,
            "test_question": 1,
        }

        response = client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        after = _counts_for_document(document_id)
        assert after == {
            "document": 0,
            "summary": 0,
            "note": 0,
            "flashcard": 0,
            "review_log": 0,
            "practice_test": 0,
            "test_question": 0,
        }
    finally:
        _delete_user(user_id)


def test_delete_document_removes_the_uploaded_file_from_disk():
    user_id, token = _create_user_and_token()
    document_id = _make_fully_populated_document(user_id)

    db = SessionLocal()
    document = db.get(Document, document_id)
    file_path = UPLOAD_DIR / document.storage_path
    db.close()

    assert file_path.exists()

    try:
        response = client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204
        assert not file_path.exists()
    finally:
        _delete_user(user_id)


def test_delete_document_missing_file_on_disk_does_not_fail_the_request():
    """If the file's already gone from disk for some reason (manually
    removed, a previous partial failure), deleting the document should
    still succeed rather than 500ing on a FileNotFoundError.
    """
    user_id, token = _create_user_and_token()
    document_id = _make_fully_populated_document(user_id)

    db = SessionLocal()
    document = db.get(Document, document_id)
    (UPLOAD_DIR / document.storage_path).unlink()
    db.close()

    try:
        response = client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204
    finally:
        _delete_user(user_id)