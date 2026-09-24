import uuid

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.practice_test import PracticeTest, TestQuestion
from app.models.user import User

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
        extracted_text="some text",
    )
    db.add(document)
    db.commit()
    document_id = document.id
    db.close()
    return document_id


def _make_practice_test(document_id: int, questions: list[tuple[str, str]]) -> tuple[int, list[int]]:
    db = SessionLocal()
    practice_test = PracticeTest(document_id=document_id)
    db.add(practice_test)
    db.flush()

    question_ids = []
    for question_text, correct_answer in questions:
        question = TestQuestion(
            practice_test_id=practice_test.id,
            question=question_text,
            correct_answer=correct_answer,
        )
        db.add(question)
        db.flush()
        question_ids.append(question.id)

    db.commit()
    practice_test_id = practice_test.id
    db.close()
    return practice_test_id, question_ids


def _delete_user_and_their_data(user_id: int) -> None:
    db = SessionLocal()
    doc_ids = [d.id for d in db.query(Document).filter(Document.user_id == user_id)]
    if doc_ids:
        test_ids = [
            t.id
            for t in db.query(PracticeTest).filter(PracticeTest.document_id.in_(doc_ids))
        ]
        if test_ids:
            db.query(TestQuestion).filter(
                TestQuestion.practice_test_id.in_(test_ids)
            ).delete(synchronize_session=False)
            db.query(PracticeTest).filter(PracticeTest.id.in_(test_ids)).delete(
                synchronize_session=False
            )
        db.query(Document).filter(Document.id.in_(doc_ids)).delete(
            synchronize_session=False
        )
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()


# ============================================================
# GET /practice-tests/{id}
# ============================================================


def test_get_practice_test_requires_auth():
    response = client.get("/practice-tests/1")
    assert response.status_code == 401


def test_get_practice_test_returns_questions_without_answers():
    user_id, token = _create_user_and_token()
    document_id = _make_document(user_id)
    practice_test_id, _ = _make_practice_test(
        document_id, [("What is a mitochondria?", "The powerhouse of the cell.")]
    )

    try:
        response = client.get(
            f"/practice-tests/{practice_test_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == practice_test_id
        assert len(body["questions"]) == 1
        assert body["questions"][0]["question"] == "What is a mitochondria?"
        # The whole point of this endpoint: never leak the answer to
        # someone who's about to take the test.
        assert "correct_answer" not in body["questions"][0]
    finally:
        _delete_user_and_their_data(user_id)


def test_get_practice_test_404s_for_other_users_test():
    owner_id, _owner_token = _create_user_and_token()
    other_id, other_token = _create_user_and_token()
    document_id = _make_document(owner_id)
    practice_test_id, _ = _make_practice_test(document_id, [("Q", "A")])

    try:
        response = client.get(
            f"/practice-tests/{practice_test_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 404
    finally:
        _delete_user_and_their_data(owner_id)
        _delete_user_and_their_data(other_id)


def test_get_practice_test_404s_for_nonexistent_test():
    _, token = _create_user_and_token()

    response = client.get(
        "/practice-tests/999999999", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


# ============================================================
# POST /practice-tests/{id}/submit
# ============================================================


def test_submit_requires_auth():
    response = client.post("/practice-tests/1/submit", json={"answers": []})
    assert response.status_code == 401


def test_submit_scores_correct_and_incorrect_answers():
    user_id, token = _create_user_and_token()
    document_id = _make_document(user_id)
    practice_test_id, question_ids = _make_practice_test(
        document_id,
        [
            ("What is a mitochondria?", "The powerhouse of the cell."),
            ("What is DNA?", "The molecule carrying genetic instructions."),
        ],
    )

    try:
        response = client.post(
            f"/practice-tests/{practice_test_id}/submit",
            json={
                "answers": [
                    {"question_id": question_ids[0], "answer": "The powerhouse of the cell."},
                    {"question_id": question_ids[1], "answer": "A protein"},
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["practice_test_id"] == practice_test_id
        assert body["score"] == 1
        assert body["total"] == 2

        results_by_id = {r["question_id"]: r for r in body["results"]}
        assert results_by_id[question_ids[0]]["is_correct"] is True
        assert results_by_id[question_ids[1]]["is_correct"] is False
        assert results_by_id[question_ids[1]]["correct_answer"] == (
            "The molecule carrying genetic instructions."
        )
    finally:
        _delete_user_and_their_data(user_id)


def test_submit_grading_ignores_case_and_surrounding_whitespace():
    user_id, token = _create_user_and_token()
    document_id = _make_document(user_id)
    practice_test_id, question_ids = _make_practice_test(
        document_id, [("What is a mitochondria?", "The powerhouse of the cell.")]
    )

    try:
        response = client.post(
            f"/practice-tests/{practice_test_id}/submit",
            json={
                "answers": [
                    {
                        "question_id": question_ids[0],
                        "answer": "  THE POWERHOUSE OF THE CELL.  ",
                    }
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["score"] == 1
    finally:
        _delete_user_and_their_data(user_id)


def test_submit_treats_missing_answer_as_incorrect_not_an_error():
    """A question the person just left blank (never included in the
    submitted answers list at all) should score as wrong, not 500 the
    request or get skipped from the results.
    """
    user_id, token = _create_user_and_token()
    document_id = _make_document(user_id)
    practice_test_id, question_ids = _make_practice_test(
        document_id, [("What is a mitochondria?", "The powerhouse of the cell.")]
    )

    try:
        response = client.post(
            f"/practice-tests/{practice_test_id}/submit",
            json={"answers": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 0
        assert body["total"] == 1
        assert body["results"][0]["question_id"] == question_ids[0]
        assert body["results"][0]["is_correct"] is False
        assert body["results"][0]["submitted_answer"] == ""
    finally:
        _delete_user_and_their_data(user_id)


def test_submit_404s_for_other_users_test():
    owner_id, _owner_token = _create_user_and_token()
    other_id, other_token = _create_user_and_token()
    document_id = _make_document(owner_id)
    practice_test_id, question_ids = _make_practice_test(document_id, [("Q", "A")])

    try:
        response = client.post(
            f"/practice-tests/{practice_test_id}/submit",
            json={"answers": [{"question_id": question_ids[0], "answer": "A"}]},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 404
    finally:
        _delete_user_and_their_data(owner_id)
        _delete_user_and_their_data(other_id)
