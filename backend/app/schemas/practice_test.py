from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
