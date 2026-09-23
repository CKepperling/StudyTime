from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.flashcard import FlashcardSource


class FlashcardOut(BaseModel):
    """Shape of a flashcard as returned by the API."""

    id: int
    document_id: int
    front: str
    back: str
    source: FlashcardSource
    ease_factor: float
    interval_days: int
    repetitions: int
    due_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlashcardCreate(BaseModel):
    """Body for manually creating a flashcard by hand - just the two
    fields a person types in; everything else (source, SM-2 scheduling
    state) is filled in server-side, same as an AI-generated card.
    """

    front: str = Field(min_length=1, max_length=2000)
    back: str = Field(min_length=1, max_length=2000)


class ReviewIn(BaseModel):
    """Body of a review submission - just the grade the user picked."""

    # 0=Again, 1=Hard, 2=Good, 3=Easy - matches the four buttons the
    # review UI shows. Bounding it here means a bad value (e.g. from a
    # buggy frontend build) gets rejected with a 422 before it ever
    # reaches the SM-2 math.
    grade: int = Field(ge=0, le=3)
