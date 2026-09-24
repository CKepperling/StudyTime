import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.practice_test import PracticeTest, TestQuestion
from app.models.user import User
from app.services.practice_test_generation import (
    MAX_QUESTIONS_PER_TEST,
    PracticeTestBatch,
    TestQuestionContent,
    generate_practice_test_questions,
)
from app.workers.tasks import generate_practice_test_task

client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


# ============================================================
# app/services/practice_test_generation.py - prompt building
# ============================================================


def test_generate_practice_test_questions_returns_gemini_questions():
    """Returns whatever questions generate_structured hands back,
    unwrapped from the PracticeTestBatch envelope Gemini's response is
    constrained to.
    """
    with patch(
        "app.services.practice_test_generation.generate_structured"
    ) as mock_generate:
        mock_generate.return_value = PracticeTestBatch(
            questions=[
                TestQuestionContent(
                    question="What is a mitochondria?",
                    correct_answer="The powerhouse of the cell.",
                ),
                TestQuestionContent(
                    question="What is DNA?",
                    correct_answer="The molecule carrying genetic instructions.",
                ),
            ]
        )

        result = generate_practice_test_questions("some extracted text")

        assert len(result) == 2
        assert result[0].question == "What is a mitochondria?"
        assert result[1].correct_answer == "The molecule carrying genetic instructions."


def test_generate_practice_test_questions_includes_source_text_in_prompt():
    """The extracted document text has to reach the prompt sent to
    Gemini - a bug that dropped it would still "work" but generate
    questions about nothing real.
    """
    with patch(
        "app.services.practice_test_generation.generate_structured"
    ) as mock_generate:
        mock_generate.return_value = PracticeTestBatch(questions=[])

        generate_practice_test_questions("a very specific sentence about mitochondria")

        prompt_sent = mock_generate.call_args.args[0]
        assert "a very specific sentence about mitochondria" in prompt_sent


def test_generate_practice_test_questions_mentions_the_batch_limit_in_the_prompt():
    """The cap on how many questions to ask for should actually appear
    in the prompt text, not just exist as an unused constant.
    """
    with patch(
        "app.services.practice_test_generation.generate_structured"
    ) as mock_generate:
        mock_generate.return_value = PracticeTestBatch(questions=[])

        generate_practice_test_questions("text")

        prompt_sent = mock_generate.call_args.args[0]
        assert str(MAX_QUESTIONS_PER_TEST) in prompt_sent


def test_generate_practice_test_questions_passes_response_schema():
    """Confirms generate_structured is called with PracticeTestBatch,
    not just some untyped dict - this is what constrains Gemini's
    output to a list of question/correct_answer pairs.
    """
    with patch(
        "app.services.practice_test_generation.generate_structured"
    ) as mock_generate:
        mock_generate.return_value = PracticeTestBatch(questions=[])

        generate_practice_test_questions("text")

        assert mock_generate.call_args.kwargs["response_schema"] is PracticeTestBatch


def test_generate_practice_test_questions_empty_batch_returns_empty_list():
    """A well-formed but empty response (Gemini decided there was
    nothing worth turning into questions) should come back as an empty
    list, not raise.
    """
    with patch(
        "app.services.practice_test_generation.generate_structured"
    ) as mock_generate:
        mock_generate.return_value = PracticeTestBatch(questions=[])

        assert generate_practice_test_questions("text") == []


# ============================================================
# app/workers/tasks.py - generate_practice_test_task
# ============================================================


@pytest.fixture
def document_with_extracted_text():
    """A real user and a real Document row with extracted_text already
    set, as if extraction already ran. Cleans up any practice test,
    the document, and the user afterward.
    """
    email = unique_email()
    db = SessionLocal()

    user = User(email=email, hashed_password="not-a-real-hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    document = Document(
        user_id=user.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="extracted",
        extracted_text="Mitochondria are the powerhouse of the cell.",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    yield document

    test_ids = [
        row[0]
        for row in db.query(PracticeTest.id)
        .filter(PracticeTest.document_id == document.id)
        .all()
    ]
    if test_ids:
        db.query(TestQuestion).filter(
            TestQuestion.practice_test_id.in_(test_ids)
        ).delete(synchronize_session=False)
        db.query(PracticeTest).filter(PracticeTest.document_id == document.id).delete()
    db.query(Document).filter(Document.id == document.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def _fake_questions(n: int) -> list[TestQuestionContent]:
    return [
        TestQuestionContent(question=f"Question {i}", correct_answer=f"Answer {i}")
        for i in range(n)
    ]


def test_generate_practice_test_task_creates_test_and_questions(
    document_with_extracted_text,
):
    document = document_with_extracted_text

    with patch("app.workers.tasks.generate_practice_test_questions") as mock_generate:
        mock_generate.return_value = _fake_questions(3)

        generate_practice_test_task(document.id)

    db = SessionLocal()
    test = (
        db.query(PracticeTest).filter(PracticeTest.document_id == document.id).first()
    )
    questions = (
        db.query(TestQuestion).filter(TestQuestion.practice_test_id == test.id).all()
    )
    db.close()

    assert test is not None
    assert len(questions) == 3
    assert {q.question for q in questions} == {"Question 0", "Question 1", "Question 2"}


def test_generate_practice_test_task_missing_document_does_not_raise():
    generate_practice_test_task(999999999)


def test_generate_practice_test_task_without_extracted_text_does_nothing():
    email = unique_email()
    db = SessionLocal()

    user = User(email=email, hashed_password="not-a-real-hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    document = Document(
        user_id=user.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        with patch("app.workers.tasks.generate_practice_test_questions") as mock_generate:
            generate_practice_test_task(document.id)
            mock_generate.assert_not_called()

        tests = (
            db.query(PracticeTest).filter(PracticeTest.document_id == document.id).all()
        )
        assert tests == []
    finally:
        db.query(Document).filter(Document.id == document.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def test_generate_practice_test_task_regenerating_replaces_old_test(
    document_with_extracted_text,
):
    """Regenerating should wipe the old test's questions and its row
    along with them, leaving exactly one practice test with the new
    question set - never two tests piled up side by side.
    """
    document = document_with_extracted_text

    with patch("app.workers.tasks.generate_practice_test_questions") as mock_generate:
        mock_generate.return_value = _fake_questions(2)
        generate_practice_test_task(document.id)

        mock_generate.return_value = _fake_questions(1)
        generate_practice_test_task(document.id)

    db = SessionLocal()
    tests = db.query(PracticeTest).filter(PracticeTest.document_id == document.id).all()
    assert len(tests) == 1
    questions = (
        db.query(TestQuestion).filter(TestQuestion.practice_test_id == tests[0].id).all()
    )
    db.close()

    assert len(questions) == 1
    assert questions[0].question == "Question 0"


# ============================================================
# GET /documents/{id}/practice-tests
# POST /documents/{id}/generate-practice-test
# ============================================================


def _signup_and_login(email: str, password: str = "testpassword123") -> str:
    client.post("/auth/signup", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_trigger_practice_test_generation_requires_extracted_text():
    email = unique_email()
    token = _signup_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    document = Document(
        user_id=user.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id
    db.close()

    try:
        response = client.post(
            f"/documents/{document_id}/generate-practice-test", headers=headers
        )
        assert response.status_code == 400
    finally:
        db = SessionLocal()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()


def test_trigger_practice_test_generation_rejects_other_users_document():
    owner_email = unique_email()
    other_email = unique_email()
    _signup_and_login(owner_email)
    other_token = _signup_and_login(other_email)

    db = SessionLocal()
    owner = db.query(User).filter(User.email == owner_email).first()
    document = Document(
        user_id=owner.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="extracted",
        extracted_text="some text",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id
    db.close()

    try:
        response = client.post(
            f"/documents/{document_id}/generate-practice-test",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 404
    finally:
        db = SessionLocal()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email.in_([owner_email, other_email])).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()


def test_trigger_practice_test_generation_starts_task_when_text_is_ready():
    email = unique_email()
    token = _signup_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    document = Document(
        user_id=user.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="extracted",
        extracted_text="Mitochondria are the powerhouse of the cell.",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id
    db.close()

    try:
        with patch(
            "app.services.practice_test_generation.generate_structured"
        ) as mock_generate:
            mock_generate.return_value = PracticeTestBatch(
                questions=_fake_questions(2)
            )

            response = client.post(
                f"/documents/{document_id}/generate-practice-test", headers=headers
            )
            assert response.status_code == 202

        # CELERY_TASK_ALWAYS_EAGER runs the task synchronously in tests,
        # so the test + questions should already exist by the time this
        # responds.
        list_response = client.get(
            f"/documents/{document_id}/practice-tests", headers=headers
        )
        assert list_response.status_code == 200
        body = list_response.json()
        assert len(body) == 1
        assert body[0]["question_count"] == 2
    finally:
        db = SessionLocal()
        test_ids = [
            row[0]
            for row in db.query(PracticeTest.id)
            .filter(PracticeTest.document_id == document_id)
            .all()
        ]
        if test_ids:
            db.query(TestQuestion).filter(
                TestQuestion.practice_test_id.in_(test_ids)
            ).delete(synchronize_session=False)
            db.query(PracticeTest).filter(
                PracticeTest.document_id == document_id
            ).delete()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()


def test_list_practice_tests_requires_auth():
    response = client.get("/documents/1/practice-tests")
    assert response.status_code == 401


def test_list_practice_tests_rejects_other_users_document():
    owner_email = unique_email()
    other_email = unique_email()
    _signup_and_login(owner_email)
    other_token = _signup_and_login(other_email)

    db = SessionLocal()
    owner = db.query(User).filter(User.email == owner_email).first()
    document = Document(
        user_id=owner.id,
        filename="lecture.pdf",
        storage_path="fake.pdf",
        status="extracted",
        extracted_text="some text",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id
    db.close()

    try:
        response = client.get(
            f"/documents/{document_id}/practice-tests",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 404
    finally:
        db = SessionLocal()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email.in_([owner_email, other_email])).delete(
            synchronize_session=False
        )
        db.commit()
        db.close()
