from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.review_log import ReviewLog
from app.services.sm2 import PASSING_GRADE

# A card that's been reviewed correctly this many times in a row is
# treated as "mastered" for dashboard purposes - matches the point in
# services/sm2.py where the interval math switches from the fixed
# 1-day/6-day steps to the ease-factor-driven formula, i.e. the card
# has graduated past the "just learning it" phase.
MASTERED_REPETITIONS = 3


@dataclass
class ProgressStats:
    total_documents: int
    total_flashcards: int
    flashcards_due_now: int
    cards_mastered: int
    reviews_today: int
    reviews_last_7_days: int
    accuracy_last_7_days: Optional[float]
    current_streak_days: int


def compute_progress_stats(db: Session, user_id: int) -> ProgressStats:
    """Aggregate one user's study activity into dashboard-ready numbers.

    Every query here is scoped to user_id, joining through Document the
    same way every other flashcard/review query in this app does - a
    Flashcard or ReviewLog has no user_id column of its own, ownership
    only exists via the Document it was generated from.
    """
    now = datetime.utcnow()  # noqa: DTZ003
    today_start = datetime.combine(now.date(), datetime.min.time())
    seven_days_ago = now - timedelta(days=7)

    total_documents = db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    ).scalar_one()

    total_flashcards = db.execute(
        select(func.count(Flashcard.id))
        .join(Document, Flashcard.document_id == Document.id)
        .where(Document.user_id == user_id)
    ).scalar_one()

    flashcards_due_now = db.execute(
        select(func.count(Flashcard.id))
        .join(Document, Flashcard.document_id == Document.id)
        .where(Document.user_id == user_id, Flashcard.due_at <= now)
    ).scalar_one()

    cards_mastered = db.execute(
        select(func.count(Flashcard.id))
        .join(Document, Flashcard.document_id == Document.id)
        .where(
            Document.user_id == user_id,
            Flashcard.repetitions >= MASTERED_REPETITIONS,
        )
    ).scalar_one()

    reviews_today = db.execute(
        select(func.count(ReviewLog.id))
        .join(Flashcard, ReviewLog.flashcard_id == Flashcard.id)
        .join(Document, Flashcard.document_id == Document.id)
        .where(Document.user_id == user_id, ReviewLog.reviewed_at >= today_start)
    ).scalar_one()

    recent_grades = (
        db.execute(
            select(ReviewLog.grade)
            .join(Flashcard, ReviewLog.flashcard_id == Flashcard.id)
            .join(Document, Flashcard.document_id == Document.id)
            .where(
                Document.user_id == user_id,
                ReviewLog.reviewed_at >= seven_days_ago,
            )
        )
        .scalars()
        .all()
    )
    reviews_last_7_days = len(recent_grades)
    accuracy_last_7_days = (
        round(
            100
            * sum(1 for grade in recent_grades if grade >= PASSING_GRADE)
            / reviews_last_7_days,
            1,
        )
        if reviews_last_7_days > 0
        else None
    )

    current_streak_days = _compute_streak(db, user_id, today=now.date())

    return ProgressStats(
        total_documents=total_documents,
        total_flashcards=total_flashcards,
        flashcards_due_now=flashcards_due_now,
        cards_mastered=cards_mastered,
        reviews_today=reviews_today,
        reviews_last_7_days=reviews_last_7_days,
        accuracy_last_7_days=accuracy_last_7_days,
        current_streak_days=current_streak_days,
    )


def _compute_streak(db: Session, user_id: int, today: date) -> int:
    """Consecutive days (most recent first) with at least one review.

    A streak still counts as "alive" if the user reviewed yesterday but
    hasn't yet today - same forgiving definition Duolingo-style streaks
    use, since otherwise every streak would show as broken first thing
    in the morning before that day's reviews happen.

    Computed in Python over a small distinct-dates result rather than
    with a recursive/window SQL query - simpler to read and test, and
    this table isn't going to have enough rows for that to matter.
    """
    review_dates = (
        db.execute(
            select(func.date(ReviewLog.reviewed_at))
            .join(Flashcard, ReviewLog.flashcard_id == Flashcard.id)
            .join(Document, Flashcard.document_id == Document.id)
            .where(Document.user_id == user_id)
            .distinct()
        )
        .scalars()
        .all()
    )
    # Some DB drivers return date objects, others return strings -
    # normalize so the comparisons below always work the same way. A
    # plain calendar date has no timezone component to preserve here,
    # so naive is correct, not an oversight - same reasoning as the
    # naive datetime.utcnow() calls elsewhere in this file.
    dates = {
        d
        if isinstance(d, date)
        else datetime.strptime(d, "%Y-%m-%d").date()  # noqa: DTZ007
        for d in review_dates
    }

    cursor = today if today in dates else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak