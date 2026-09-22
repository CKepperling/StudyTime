from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

# Grades match the four review buttons the frontend will show:
# 0 = Again, 1 = Hard, 2 = Good, 3 = Easy.
GRADE_AGAIN = 0
GRADE_HARD = 1
GRADE_GOOD = 2
GRADE_EASY = 3

# Anything below this counts as a "failed" review in classic SM-2 (which
# uses a 0-5 scale and treats <3 as a miss). On our 0-3 scale, only
# "Again" is a genuine miss - Hard/Good/Easy all count as a pass, just
# with different confidence.
PASSING_GRADE = GRADE_HARD

MIN_EASE_FACTOR = 1.3


@dataclass
class SM2Result:
    """The new scheduling state for a flashcard after a review.

    Kept separate from the Flashcard model so this module has no
    dependency on SQLAlchemy - it's pure math, easy to unit test on
    its own, and the caller decides how to persist it.
    """

    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: datetime


def review_flashcard(
    grade: int,
    ease_factor: float,
    interval_days: int,
    repetitions: int,
    reviewed_at: Optional[datetime] = None,
) -> SM2Result:
    """Apply one SM-2 review to a flashcard's current scheduling state.

    This is the standard SuperMemo SM-2 algorithm, adapted from its
    usual 0-5 grade scale down to our 4 review buttons (0-3). A failed
    review (grade 0, "Again") resets progress entirely so the card
    comes back for review almost immediately, rather than drifting
    further out on a schedule it clearly isn't ready for.
    """
    if reviewed_at is None:
        # Naive UTC on purpose - due_at and every other timestamp on
        # Flashcard is stored the same way (see Flashcard.due_at's own
        # `default=datetime.utcnow`), so mixing in a tz-aware value here
        # would raise on comparison instead of making things safer.
        reviewed_at = datetime.utcnow()  # noqa: DTZ003

    # The ease factor update formula is SM-2's own, taken directly from
    # the original algorithm (mapped onto our 0-3 scale by scaling grade
    # up to fit the 0-5 range the formula expects).
    scaled_grade = grade * (5 / GRADE_EASY)
    new_ease_factor = ease_factor + (
        0.1 - (5 - scaled_grade) * (0.08 + (5 - scaled_grade) * 0.02)
    )
    new_ease_factor = max(new_ease_factor, MIN_EASE_FACTOR)

    if grade < PASSING_GRADE:
        # A miss - start the repetition count over and bring the card
        # back tomorrow rather than trusting the old interval.
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * new_ease_factor)

    due_at = reviewed_at + timedelta(days=new_interval)

    return SM2Result(
        ease_factor=new_ease_factor,
        interval_days=new_interval,
        repetitions=new_repetitions,
        due_at=due_at,
    )
