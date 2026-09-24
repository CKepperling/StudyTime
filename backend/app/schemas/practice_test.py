from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TestQuestionOut(BaseModel):
    """A question as shown to someone taking the test - deliberately
    leaves correct_answer out. Revealing it here would let a person
    read the answer straight out of the network response before
    submitting, which defeats the point of taking the test.
    """

    id: int
    question: str

    model_config = ConfigDict(from_attributes=True)


class PracticeTestOut(BaseModel):
    """A practice test plus the questions to take it - the shape
    GET /practice-tests/{id} returns.
    """

    id: int
    document_id: int
    created_at: datetime
    questions: list[TestQuestionOut]

    model_config = ConfigDict(from_attributes=True)


class PracticeTestSummaryOut(BaseModel):
    """A practice test's own metadata without its questions - the shape
    GET /documents/{id}/practice-tests returns, since a document detail
    page just needs to know a test exists (and how big it is) before
    someone opts to take it.
    """

    id: int
    document_id: int
    created_at: datetime
    question_count: int

    model_config = ConfigDict(from_attributes=True)


class AnswerIn(BaseModel):
    """One answer in a test submission - what the person typed for a
    single question, matched back up to it by question_id.
    """

    question_id: int
    answer: str = Field(min_length=0, max_length=2000)


class SubmissionIn(BaseModel):
    """Body of POST /practice-tests/{id}/submit - every answer the
    person is submitting for that test, in one request rather than one
    call per question.
    """

    answers: list[AnswerIn]


class AnswerResult(BaseModel):
    """One graded answer - echoes back the question, what the person
    answered, whether it was judged correct, and the correct answer so
    the results view can show what they missed.
    """

    question_id: int
    question: str
    submitted_answer: str
    correct_answer: str
    is_correct: bool


class SubmissionResult(BaseModel):
    """The graded outcome of a whole test submission."""

    practice_test_id: int
    score: int
    total: int
    results: list[AnswerResult]
