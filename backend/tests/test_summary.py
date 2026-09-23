import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models.document import Document
from app.models.summary import DifficultyLevel, Summary
from app.models.user import User
from app.services.summary import SummaryContent, generate_summary
from app.workers.tasks import generate_summaries

client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


# ============================================================
# app/services/summary.py - prompt building, one level at a time
# ============================================================


@pytest.mark.parametrize("level", list(DifficultyLevel))
def test_generate_summary_returns_gemini_text(level):
    """For every level, the function returns whatever text
    generate_structured hands back - it doesn't transform or wrap it.
    """
    with patch("app.services.summary.generate_structured") as mock_generate:
        mock_generate.return_value = SummaryContent(text="a generated summary")

        result = generate_summary("some extracted text", level)

        assert result == "a generated summary"


@pytest.mark.parametrize("level", list(DifficultyLevel))
def test_generate_summary_includes_source_text_in_prompt(level):
    """The actual extracted document text has to reach the prompt sent
    to Gemini - a bug that dropped it would still "work" (return some
    string) but summarize nothing real.
    """
    with patch("app.services.summary.generate_structured") as mock_generate:
        mock_generate.return_value = SummaryContent(text="summary")

        generate_summary("a very specific sentence about mitochondria", level)

        prompt_sent = mock_generate.call_args.args[0]
        assert "a very specific sentence about mitochondria" in prompt_sent


def test_generate_summary_uses_different_instructions_per_level():
    """Easy, medium, and hard should produce genuinely different
    prompts - not the same instruction with the level name swapped in,
    which would defeat the entire point of having levels.
    """
    prompts = {}
    with patch("app.services.summary.generate_structured") as mock_generate:
        mock_generate.return_value = SummaryContent(text="summary")

        for level in DifficultyLevel:
            generate_summary("text", level)
            prompts[level] = mock_generate.call_args.args[0]

    assert prompts[DifficultyLevel.EASY] != prompts[DifficultyLevel.MEDIUM]
    assert prompts[DifficultyLevel.MEDIUM] != prompts[DifficultyLevel.HARD]
    assert prompts[DifficultyLevel.EASY] != prompts[DifficultyLevel.HARD]


def test_generate_summary_passes_response_schema():
    """Confirms generate_structured is actually called with
    SummaryContent, not just some untyped dict - this is what makes
    Gemini's output schema-constrained rather than free-form JSON.
    """
    with patch("app.services.summary.generate_structured") as mock_generate:
        mock_generate.return_value = SummaryContent(text="summary")

        generate_summary("text", DifficultyLevel.MEDIUM)

        assert mock_generate.call_args.kwargs["response_schema"] is SummaryContent


# ============================================================
# app/workers/tasks.py - generate_summaries, the orchestration task
# ============================================================


@pytest.fixture
def document_with_extracted_text():
    """A real user and a real Document row with extracted_text already
    set, as if extraction already ran - generate_summaries doesn't care
    HOW the text got there, just that it's present. Cleans up summaries,
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

    db.query(Summary).filter(Summary.document_id == document.id).delete()
    db.query(Document).filter(Document.id == document.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()
    db.close()


def test_generate_summaries_creates_one_row_per_level(document_with_extracted_text):
    document = document_with_extracted_text

    with patch("app.workers.tasks.generate_summary") as mock_generate:
        mock_generate.side_effect = lambda text, level: f"summary at {level.value}"

        generate_summaries(document.id)

    db = SessionLocal()
    summaries = db.query(Summary).filter(Summary.document_id == document.id).all()
    db.close()

    assert len(summaries) == 3
    levels_created = {s.difficulty_level for s in summaries}
    assert levels_created == {
        DifficultyLevel.EASY,
        DifficultyLevel.MEDIUM,
        DifficultyLevel.HARD,
    }


def test_generate_summaries_missing_document_does_not_raise():
    # No such document - should return quietly, same reasoning as
    # extract_document_text's identical check.
    generate_summaries(999999999)


def test_generate_summaries_without_extracted_text_does_nothing():
    email = unique_email()
    db = SessionLocal()

    user = User(email=email, hashed_password="not-a-real-hash")
    db.add(user)
    db.commit()
    db.refresh(user)

    # extracted_text left as None - as if extraction hasn't run yet,
    # or landed on no_text_found/extraction_failed instead.
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
        with patch("app.workers.tasks.generate_summary") as mock_generate:
            generate_summaries(document.id)
            mock_generate.assert_not_called()

        summaries = db.query(Summary).filter(Summary.document_id == document.id).all()
        assert summaries == []
    finally:
        db.query(Document).filter(Document.id == document.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()


def test_generate_summaries_replaces_existing_summaries(document_with_extracted_text):
    """Calling this twice (the manual "regenerate" path) should leave
    exactly 3 rows, with fresh content - not 6 rows, and not the old
    content sitting there unchanged.
    """
    document = document_with_extracted_text

    with patch("app.workers.tasks.generate_summary") as mock_generate:
        mock_generate.return_value = "the old summary"
        generate_summaries(document.id)

        mock_generate.return_value = "the new summary"
        generate_summaries(document.id)

    db = SessionLocal()
    summaries = db.query(Summary).filter(Summary.document_id == document.id).all()
    db.close()

    assert len(summaries) == 3
    assert all(s.content == "the new summary" for s in summaries)