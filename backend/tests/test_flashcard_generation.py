import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.user import User
from app.services.flashcard_generation import (
    MAX_FLASHCARDS_PER_DOCUMENT,
    FlashcardBatch,
    FlashcardContent,
    generate_flashcards,
)
from app.workers.tasks import generate_flashcards_task

client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


# ============================================================
# app/services/flashcard_generation.py - prompt building
# ============================================================


def test_generate_flashcards_returns_gemini_cards():
    """Returns whatever cards generate_structured hands back, unwrapped
    from the FlashcardBatch envelope Gemini's response is constrained to.
    """
    with patch("app.services.flashcard_generation.generate_structured") as mock_generate:
        mock_generate.return_value = FlashcardBatch(
            cards=[
                FlashcardContent(front="What is a mitochondria?", back="The powerhouse of the cell."),
                FlashcardContent(front="What is DNA?", back="The molecule carrying genetic instructions."),
            ]
        )

        result = generate_flashcards("some extracted text")

        assert len(result) == 2
        assert result[0].front == "What is a mitochondria?"
        assert result[1].back == "The molecule carrying genetic instructions."


def test_generate_flashcards_includes_source_text_in_prompt():
    """The extracted document text has to reach the prompt sent to
    Gemini - a bug that dropped it would still "work" but generate
    cards about nothing real.
    """
    with patch("app.services.flashcard_generation.generate_structured") as mock_generate:
        mock_generate.return_value = FlashcardBatch(cards=[])

        generate_flashcards("a very specific sentence about mitochondria")

        prompt_sent = mock_generate.call_args.args[0]
        assert "a very specific sentence about mitochondria" in prompt_sent


def test_generate_flashcards_mentions_the_batch_limit_in_the_prompt():
    """The cap on how many cards to ask for should actually appear in
    the prompt text, not just exist as an unused constant.
    """
    with patch("app.services.flashcard_generation.generate_structured") as mock_generate:
        mock_generate.return_value = FlashcardBatch(cards=[])

        generate_flashcards("text")

        prompt_sent = mock_generate.call_args.args[0]
        assert str(MAX_FLASHCARDS_PER_DOCUMENT) in prompt_sent


def test_generate_flashcards_passes_response_schema():
    """Confirms generate_structured is called with FlashcardBatch, not
    just some untyped dict - this is what constrains Gemini's output to
    a list of front/back pairs.
    """
    with patch("app.services.flashcard_generation.generate_structured") as mock_generate:
        mock_generate.return_value = FlashcardBatch(cards=[])

        generate_flashcards("text")

        assert mock_generate.call_args.kwargs["response_schema"] is FlashcardBatch


def test_generate_flashcards_empty_batch_returns_empty_list():
    """A well-formed but empty response (Gemini decided there was
    nothing worth turning into cards) should come back as an empty
    list, not raise.
    """
    with patch("app.services.flashcard_generation.generate_structured") as mock_generate:
        mock_generate.return_value = FlashcardBatch(cards=[])

        assert generate_flashcards("text") == []


# ============================================================
# app/workers/tasks.py - generate_flashcards_task, the orchestration task
# ============================================================


@pytest.fixture
def document_with_extracted_text():
    """A real user and a real Document row with extracted_text already
    set, as if extraction already ran. Cleans up flashcards, the
    document, and the user afterward.
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

    db.query(Flashcard).filter(Flashcard.document_id == document.id).delete()
    db.query(Document).filter(Document.id == document.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def _fake_cards(n: int) -> list[FlashcardContent]:
    return [
        FlashcardContent(front=f"Question {i}", back=f"Answer {i}") for i in range(n)
    ]


def test_generate_flashcards_task_creates_ai_generated_rows(document_with_extracted_text):
    document = document_with_extracted_text

    with patch("app.workers.tasks.generate_flashcards") as mock_generate:
        mock_generate.return_value = _fake_cards(3)

        generate_flashcards_task(document.id)

    db = SessionLocal()
    cards = db.query(Flashcard).filter(Flashcard.document_id == document.id).all()
    db.close()

    assert len(cards) == 3
    assert all(c.source == FlashcardSource.AI_GENERATED for c in cards)
    assert {c.front for c in cards} == {"Question 0", "Question 1", "Question 2"}


def test_generate_flashcards_task_missing_document_does_not_raise():
    generate_flashcards_task(999999999)


def test_generate_flashcards_task_without_extracted_text_does_nothing():
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
        with patch("app.workers.tasks.generate_flashcards") as mock_generate:
            generate_flashcards_task(document.id)
            mock_generate.assert_not_called()

        cards = db.query(Flashcard).filter(Flashcard.document_id == document.id).all()
        assert cards == []
    finally:
        db.query(Document).filter(Document.id == document.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def test_generate_flashcards_task_replaces_only_ai_generated_cards(
    document_with_extracted_text,
):
    """Regenerating should wipe the old AI cards and replace them, but
    must never touch a card the user created by hand - that would throw
    away work someone typed themselves just because they clicked
    "regenerate."
    """
    document = document_with_extracted_text

    db = SessionLocal()
    manual_card = Flashcard(
        document_id=document.id,
        front="My own question",
        back="My own answer",
        source=FlashcardSource.MANUAL,
    )
    db.add(manual_card)
    db.commit()
    db.close()

    with patch("app.workers.tasks.generate_flashcards") as mock_generate:
        mock_generate.return_value = _fake_cards(2)
        generate_flashcards_task(document.id)

        mock_generate.return_value = _fake_cards(1)
        generate_flashcards_task(document.id)

    db = SessionLocal()
    cards = db.query(Flashcard).filter(Flashcard.document_id == document.id).all()
    db.close()

    ai_cards = [c for c in cards if c.source == FlashcardSource.AI_GENERATED]
    manual_cards = [c for c in cards if c.source == FlashcardSource.MANUAL]

    assert len(ai_cards) == 1
    assert len(manual_cards) == 1
    assert manual_cards[0].front == "My own question"


# ============================================================
# POST /documents/{id}/generate-flashcards
# ============================================================


def _signup_and_login(email: str, password: str = "testpassword123") -> str:
    client.post("/auth/signup", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def test_trigger_flashcard_generation_requires_extracted_text():
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
            f"/documents/{document_id}/generate-flashcards", headers=headers
        )
        assert response.status_code == 400
    finally:
        db = SessionLocal()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()


def test_trigger_flashcard_generation_rejects_other_users_document():
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
            f"/documents/{document_id}/generate-flashcards",
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


def test_trigger_flashcard_generation_starts_task_when_text_is_ready():
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
            "app.services.flashcard_generation.generate_structured"
        ) as mock_generate:
            mock_generate.return_value = FlashcardBatch(cards=_fake_cards(2))

            response = client.post(
                f"/documents/{document_id}/generate-flashcards", headers=headers
            )
            assert response.status_code == 202

        db = SessionLocal()
        cards = (
            db.query(Flashcard).filter(Flashcard.document_id == document_id).all()
        )
        db.close()
        # CELERY_TASK_ALWAYS_EAGER runs the task synchronously in tests,
        # so the cards should already exist by the time this responds.
        assert len(cards) == 2
    finally:
        db = SessionLocal()
        db.query(Flashcard).filter(Flashcard.document_id == document_id).delete()
        db.query(Document).filter(Document.id == document_id).delete()
        db.query(User).filter(User.email == email).delete()
        db.commit()
        db.close()
