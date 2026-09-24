import os

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.db import SessionLocal
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.practice_test import PracticeTest, TestQuestion
from app.models.summary import DifficultyLevel, Summary
from app.services.flashcard_generation import generate_flashcards
from app.services.practice_test_generation import generate_practice_test_questions
from app.services.summary import generate_summary
from app.storage import UPLOAD_DIR
from app.workers.celery_app import celery_app


@celery_app.task(name="extract_document_text")
def extract_document_text(document_id: int) -> None:
    """Pull the text out of an uploaded PDF and store it on the Document row.

    Runs in the Celery worker process, not the web request - this task
    is what api/documents.py's upload_document() hands off to via
    .delay(), so the person who uploaded the file gets an immediate
    201 response instead of waiting on however long extraction takes.

    Opens its own DB session rather than reusing one from a request,
    since this runs in a completely separate process (or synchronously
    in-process during tests, if CELERY_TASK_ALWAYS_EAGER is set) with
    no request-scoped session to borrow.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            # Deleted (or never committed - shouldn't happen) before the
            # worker got to it. Nothing to extract text into.
            return

        document.status = "processing"
        db.commit()

        try:
            reader = PdfReader(str(UPLOAD_DIR / document.storage_path))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, FileNotFoundError, OSError):
            # Corrupt PDF, an encrypted one pypdf can't open, or the
            # file's gone missing from disk - record the failure rather
            # than leaving the document stuck at "processing" forever.
            document.status = "extraction_failed"
            db.commit()
            return

        document.extracted_text = text
        # A PDF that's all images (scanned lecture slides with no
        # actual text layer) parses fine but yields nothing usable -
        # that's a distinct outcome from a hard extraction error, since
        # T31 (non-PDF/OCR support) is the eventual fix for it, not a bug
        # in this task.
        document.status = "extracted" if text.strip() else "no_text_found"
        db.commit()

        # Off by default - see AUTO_GENERATE_SUMMARIES in .env.example.
        # While the team's Gemini key is capped at a tight free-tier
        # daily quota, summaries are triggered manually instead (the
        # POST /documents/{id}/generate-summaries endpoint in
        # api/documents.py) so uploading a document during testing
        # doesn't silently spend 3 calls every time. Flip this to
        # "true" before a demo for the nicer automatic experience.
        auto_generate = os.environ.get("AUTO_GENERATE_SUMMARIES", "false").lower() == "true"
        if auto_generate and document.status == "extracted":
            generate_summaries.delay(document_id)

        auto_generate_cards = (
            os.environ.get("AUTO_GENERATE_FLASHCARDS", "false").lower() == "true"
        )
        if auto_generate_cards and document.status == "extracted":
            generate_flashcards_task.delay(document_id)

        auto_generate_test = (
            os.environ.get("AUTO_GENERATE_PRACTICE_TESTS", "false").lower() == "true"
        )
        if auto_generate_test and document.status == "extracted":
            generate_practice_test_task.delay(document_id)
    finally:
        db.close()


@celery_app.task(name="generate_summaries")
def generate_summaries(document_id: int) -> None:
    """Generate one Summary row per difficulty level for a document.

    This single task covers BOTH "generate for the first time" (chained
    automatically after extraction, if AUTO_GENERATE_SUMMARIES is on)
    and "regenerate" (the manual POST /generate-summaries endpoint calls
    this exact same task) - there's no separate regenerate code path.

    Existing summaries for this document are deleted first, so calling
    this a second time replaces the old easy/medium/hard set rather than
    piling up duplicate rows alongside them.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or not document.extracted_text:
            # Nothing to summarize - either the document's gone, or
            # extraction hasn't produced usable text yet (still
            # pending/processing, or landed on no_text_found /
            # extraction_failed instead of extracted).
            return

        db.query(Summary).filter(Summary.document_id == document_id).delete()

        for level in DifficultyLevel:
            content = generate_summary(document.extracted_text, level)
            db.add(
                Summary(
                    document_id=document_id,
                    difficulty_level=level,
                    content=content,
                )
            )

        db.commit()
    finally:
        db.close()


@celery_app.task(name="generate_flashcards_task")
def generate_flashcards_task(document_id: int) -> None:
    """Generate a set of AI flashcards for a document.

    Same "generate or regenerate" duality as generate_summaries above:
    this one task is chained automatically after extraction (if
    AUTO_GENERATE_FLASHCARDS is on) and is also what the manual
    POST /generate-flashcards endpoint calls directly.

    Only AI-generated cards for this document are deleted before
    regenerating - any cards the user added by hand (FlashcardSource.MANUAL,
    from T13.5's manual-creation endpoint) are left alone. Wiping those
    out just because someone clicked "regenerate flashcards" would throw
    away work the user typed themselves.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or not document.extracted_text:
            # Nothing to generate from - either the document's gone, or
            # extraction hasn't produced usable text yet.
            return

        db.query(Flashcard).filter(
            Flashcard.document_id == document_id,
            Flashcard.source == FlashcardSource.AI_GENERATED,
        ).delete()

        cards = generate_flashcards(document.extracted_text)
        for card in cards:
            db.add(
                Flashcard(
                    document_id=document_id,
                    front=card.front,
                    back=card.back,
                    source=FlashcardSource.AI_GENERATED,
                )
            )

        db.commit()
    finally:
        db.close()


@celery_app.task(name="generate_practice_test_task")
def generate_practice_test_task(document_id: int) -> None:
    """Generate a fresh practice test (a PracticeTest plus its TestQuestion
    rows) for a document.

    Same "generate or regenerate" duality as generate_summaries and
    generate_flashcards_task above - chained automatically after
    extraction (if AUTO_GENERATE_PRACTICE_TESTS is on) and also what the
    manual POST /generate-practice-test endpoint calls directly.

    Unlike flashcards, a practice test has no manually-created rows to
    preserve, so regenerating simply replaces the document's existing
    test(s) wholesale. TestQuestion rows are deleted before their parent
    PracticeTest rows - there's no ON DELETE CASCADE on the FK, and no
    cascade configured on the ORM relationship either, so deleting a
    PracticeTest first would violate the foreign key.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or not document.extracted_text:
            # Nothing to generate from - either the document's gone, or
            # extraction hasn't produced usable text yet.
            return

        existing_test_ids = [
            row[0]
            for row in db.query(PracticeTest.id)
            .filter(PracticeTest.document_id == document_id)
            .all()
        ]
        if existing_test_ids:
            db.query(TestQuestion).filter(
                TestQuestion.practice_test_id.in_(existing_test_ids)
            ).delete(synchronize_session=False)
            db.query(PracticeTest).filter(
                PracticeTest.document_id == document_id
            ).delete(synchronize_session=False)

        practice_test = PracticeTest(document_id=document_id)
        db.add(practice_test)
        db.flush()  # assigns practice_test.id for the questions below

        questions = generate_practice_test_questions(document.extracted_text)
        for question in questions:
            db.add(
                TestQuestion(
                    practice_test_id=practice_test.id,
                    question=question.question,
                    correct_answer=question.correct_answer,
                )
            )

        db.commit()
    finally:
        db.close()