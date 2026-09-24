from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.practice_test import PracticeTest
from app.models.user import User
from app.schemas.practice_test import (
    AnswerResult,
    PracticeTestOut,
    SubmissionIn,
    SubmissionResult,
)

router = APIRouter(prefix="/practice-tests", tags=["practice-tests"])


def _get_owned_practice_test(
    practice_test_id: int, current_user: User, db: Session
) -> PracticeTest:
    """Same ownership-through-Document pattern as flashcards.py's
    _get_owned_flashcard - a PracticeTest has no user_id of its own,
    ownership only exists via the Document it was generated from.

    Eagerly loads .questions in the same query, since both endpoints
    below need them and the test is typically tiny (up to
    MAX_QUESTIONS_PER_TEST rows) - not worth a second round trip.
    """
    practice_test = (
        db.execute(
            select(PracticeTest)
            .join(Document, PracticeTest.document_id == Document.id)
            .where(
                PracticeTest.id == practice_test_id,
                Document.user_id == current_user.id,
            )
            .options(selectinload(PracticeTest.questions))
        )
        .scalars()
        .first()
    )
    if practice_test is None:
        # Same 404 whether the test doesn't exist at all or belongs to
        # someone else - not leaking which one it is.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice test not found"
        )
    return practice_test


@router.get("/{practice_test_id}", response_model=PracticeTestOut)
def get_practice_test(
    practice_test_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What someone taking the test loads - the questions, but not the
    answers (TestQuestionOut in the response schema leaves correct_answer
    out entirely).
    """
    return _get_owned_practice_test(practice_test_id, current_user, db)


def _normalize(text: str) -> str:
    """Loose equality for short-answer grading - trims surrounding
    whitespace and ignores case, so "Mitochondria", "mitochondria ",
    and "MITOCHONDRIA" all count as the same answer. Doesn't try to
    handle synonyms or partial credit - that would need an AI grading
    call, which is more than a short-answer practice test needs.
    """
    return text.strip().lower()


@router.post("/{practice_test_id}/submit", response_model=SubmissionResult)
def submit_practice_test(
    practice_test_id: int,
    submission: SubmissionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grade a full test submission in one call and hand back a
    per-question breakdown plus the overall score.

    Nothing about a submission or its score is persisted - a practice
    test is meant to be retaken freely, and there's no "attempt
    history" feature (yet) that would need a row to attach to.
    """
    practice_test = _get_owned_practice_test(practice_test_id, current_user, db)

    answers_by_question_id = {
        answer.question_id: answer.answer for answer in submission.answers
    }

    results = []
    score = 0
    for question in practice_test.questions:
        submitted_answer = answers_by_question_id.get(question.id, "")
        is_correct = _normalize(submitted_answer) == _normalize(question.correct_answer)
        if is_correct:
            score += 1

        results.append(
            AnswerResult(
                question_id=question.id,
                question=question.question,
                submitted_answer=submitted_answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
            )
        )

    return SubmissionResult(
        practice_test_id=practice_test.id,
        score=score,
        total=len(practice_test.questions),
        results=results,
    )
