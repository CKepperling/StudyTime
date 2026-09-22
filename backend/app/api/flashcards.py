from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.review_log import ReviewLog
from app.models.user import User
from app.schemas.flashcard import FlashcardOut, ReviewIn
from app.services.sm2 import review_flashcard

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("/due", response_model=list[FlashcardOut])
def list_due_flashcards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Flashcards belonging to the current user that are due for review.

    Joins through Document rather than adding a user_id directly onto
    Flashcard - the ownership check has to go through the document a
    card was generated from, same as everywhere else in this API.
    """
    flashcards = (
        db.execute(
            select(Flashcard)
            .join(Document, Flashcard.document_id == Document.id)
            .where(
                Document.user_id == current_user.id,
                # Naive UTC to match Flashcard.due_at's own storage
                # format - see the comment in services/sm2.py.
                Flashcard.due_at <= datetime.utcnow(),  # noqa: DTZ003
            )
            .order_by(Flashcard.due_at.asc())
        )
        .scalars()
        .all()
    )
    return flashcards


def _get_owned_flashcard(
    flashcard_id: int, current_user: User, db: Session
) -> Flashcard:
    flashcard = (
        db.execute(
            select(Flashcard)
            .join(Document, Flashcard.document_id == Document.id)
            .where(Flashcard.id == flashcard_id, Document.user_id == current_user.id)
        )
        .scalars()
        .first()
    )
    if flashcard is None:
        # Same 404 whether the card doesn't exist at all or belongs to
        # someone else - not leaking which one it is.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found"
        )
    return flashcard


@router.post("/{flashcard_id}/review", response_model=FlashcardOut)
def submit_review(
    flashcard_id: int,
    review: ReviewIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    flashcard = _get_owned_flashcard(flashcard_id, current_user, db)

    result = review_flashcard(
        grade=review.grade,
        ease_factor=flashcard.ease_factor,
        interval_days=flashcard.interval_days,
        repetitions=flashcard.repetitions,
    )

    flashcard.ease_factor = result.ease_factor
    flashcard.interval_days = result.interval_days
    flashcard.repetitions = result.repetitions
    flashcard.due_at = result.due_at

    db.add(ReviewLog(flashcard_id=flashcard.id, grade=review.grade))
    db.commit()
    db.refresh(flashcard)

    return flashcard
