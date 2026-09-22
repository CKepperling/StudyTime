from datetime import datetime, timedelta, timezone

from app.services.sm2 import review_flashcard

# Naive on purpose (matches how Flashcard.due_at is stored - see the
# comment in app/services/sm2.py) - built from a tz-aware value and
# then stripped, rather than calling datetime(...) with no tzinfo
# directly, just to keep ruff's DTZ001 happy.
FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)


def test_first_review_good_sets_one_day_interval():
    result = review_flashcard(
        grade=2,  # Good
        ease_factor=2.5,
        interval_days=0,
        repetitions=0,
        reviewed_at=FIXED_NOW,
    )

    assert result.repetitions == 1
    assert result.interval_days == 1
    assert result.due_at == FIXED_NOW + timedelta(days=1)


def test_second_consecutive_good_review_sets_six_day_interval():
    result = review_flashcard(
        grade=2,
        ease_factor=2.5,
        interval_days=1,
        repetitions=1,
        reviewed_at=FIXED_NOW,
    )

    assert result.repetitions == 2
    assert result.interval_days == 6


def test_third_review_multiplies_interval_by_ease_factor():
    result = review_flashcard(
        grade=2,
        ease_factor=2.5,
        interval_days=6,
        repetitions=2,
        reviewed_at=FIXED_NOW,
    )

    assert result.repetitions == 3
    # interval * ease_factor, rounded - the new ease_factor shifts
    # slightly from a "Good" grade, so this checks the actual math
    # rather than assuming ease_factor stayed exactly 2.5.
    assert result.interval_days == round(6 * result.ease_factor)


def test_failing_grade_resets_repetitions_and_interval():
    result = review_flashcard(
        grade=0,  # Again
        ease_factor=2.8,
        interval_days=15,
        repetitions=4,
        reviewed_at=FIXED_NOW,
    )

    assert result.repetitions == 0
    assert result.interval_days == 1
    assert result.due_at == FIXED_NOW + timedelta(days=1)


def test_easy_grade_increases_ease_factor():
    result = review_flashcard(
        grade=3,  # Easy
        ease_factor=2.5,
        interval_days=6,
        repetitions=2,
        reviewed_at=FIXED_NOW,
    )

    assert result.ease_factor > 2.5


def test_hard_grade_decreases_ease_factor_but_still_passes():
    result = review_flashcard(
        grade=1,  # Hard - passes (repetitions increase) but ease drops
        ease_factor=2.5,
        interval_days=6,
        repetitions=2,
        reviewed_at=FIXED_NOW,
    )

    assert result.ease_factor < 2.5
    assert result.repetitions == 3


def test_ease_factor_never_drops_below_minimum():
    result = review_flashcard(
        grade=0,
        ease_factor=1.3,
        interval_days=1,
        repetitions=0,
        reviewed_at=FIXED_NOW,
    )

    assert result.ease_factor >= 1.3


def test_defaults_to_current_time_when_not_provided():
    before = datetime.utcnow()  # noqa: DTZ003
    result = review_flashcard(grade=2, ease_factor=2.5, interval_days=0, repetitions=0)
    after = datetime.utcnow()  # noqa: DTZ003

    # due_at should be ~1 day after "now" - just confirm it landed in a
    # sane window rather than pinning to a millisecond-exact value.
    assert before + timedelta(days=1) <= result.due_at <= after + timedelta(days=1)
