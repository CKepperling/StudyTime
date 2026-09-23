import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.flashcard import Flashcard, FlashcardSource
from app.models.summary import Summary
from app.models.user import User
from app.schemas.document import DocumentOut
from app.schemas.flashcard import FlashcardCreate, FlashcardOut
from app.schemas.summary import SummaryOut
from app.storage import UPLOAD_DIR
from app.workers.tasks import (
    extract_document_text,
    generate_flashcards_task,
    generate_summaries,
)

router = APIRouter(prefix="/documents", tags=["documents"])

# Generous enough for lecture-slide PDFs; just a backstop against
# someone filling the disk with one absurd upload. The extraction
# worker may end up wanting its own, separate limit for how much text
# it's willing to process.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported right now",
        )

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large (max 20MB)",
        )

    # A random name on disk - not the user's original filename - so two
    # people uploading "notes.pdf" never collide, and nobody can request
    # another user's file just by guessing its display name.
    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(contents)

    document = Document(
        user_id=current_user.id,
        filename=file.filename or storage_path,
        storage_path=storage_path,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Hand off to the Celery worker rather than extracting text inline
    # here - a multi-page PDF can take real time to process, and this
    # request shouldn't make the person wait on it just to get back
    # "yes, I received your file."
    extract_document_text.delay(document.id)

    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every document the CURRENT user uploaded - never another user's.

    Filtering by current_user.id here (rather than trusting a query
    param) is what stops one logged-in user from listing or paging
    through everyone else's uploads.
    """
    documents = (
        db.execute(
            select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(Document.created_at.desc())
        )
        .scalars()
        .all()
    )
    return documents


@router.get("/{document_id}/flashcards", response_model=list[FlashcardOut])
def list_document_flashcards(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every flashcard generated from one of the current user's documents.

    404s (rather than returning an empty list) when the document
    itself doesn't exist or belongs to someone else - same reasoning
    as flashcards.py's _get_owned_flashcard, so a caller can't tell
    "no cards yet" apart from "not your document" by trying IDs.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    flashcards = (
        db.execute(
            select(Flashcard)
            .where(Flashcard.document_id == document_id)
            .order_by(Flashcard.created_at.asc())
        )
        .scalars()
        .all()
    )
    return flashcards


@router.post(
    "/{document_id}/flashcards",
    response_model=FlashcardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_flashcard(
    document_id: int,
    flashcard_in: FlashcardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a flashcard by hand to one of the current user's documents.

    Marked FlashcardSource.MANUAL so a later "regenerate AI flashcards"
    call (generate_flashcards_task) knows to leave this one alone
    instead of deleting it along with the AI-generated set.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    flashcard = Flashcard(
        document_id=document_id,
        front=flashcard_in.front,
        back=flashcard_in.back,
        source=FlashcardSource.MANUAL,
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)

    return flashcard


@router.get("/{document_id}/summaries", response_model=list[SummaryOut])
def list_document_summaries(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every summary generated for one of the current user's documents -
    typically three rows (easy/medium/hard) once generation has run.

    Same 404-not-empty-list reasoning as list_document_flashcards above:
    a caller shouldn't be able to distinguish "no summaries yet" from
    "not your document" by trying different ids.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    summaries = (
        db.execute(
            select(Summary)
            .where(Summary.document_id == document_id)
            .order_by(Summary.created_at.asc())
        )
        .scalars()
        .all()
    )
    return summaries


@router.post(
    "/{document_id}/generate-summaries", status_code=status.HTTP_202_ACCEPTED
)
def trigger_summary_generation(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually kick off summary generation (or regeneration) for a document.

    This is the deliberate "manual trigger" path instead of automatic
    generation on every upload - see AUTO_GENERATE_SUMMARIES in
    tasks.py for why. Calling this again after summaries already exist
    replaces them (generate_summaries deletes the old set first), so
    this endpoint doubles as "regenerate."
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text hasn't been extracted yet - try again shortly",
        )

    generate_summaries.delay(document_id)
    return {"detail": "Summary generation started"}


@router.post(
    "/{document_id}/generate-flashcards", status_code=status.HTTP_202_ACCEPTED
)
def trigger_flashcard_generation(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually kick off AI flashcard generation (or regeneration) for a
    document - same manual-trigger reasoning as trigger_summary_generation
    above. Regenerating replaces only the AI-generated cards; anything the
    user added by hand through the manual-creation endpoint is untouched.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text hasn't been extracted yet - try again shortly",
        )

    generate_flashcards_task.delay(document_id)
    return {"detail": "Flashcard generation started"}