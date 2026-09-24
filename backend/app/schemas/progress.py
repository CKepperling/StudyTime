from typing import Optional

from pydantic import BaseModel


class ProgressOut(BaseModel):
    """Shape of the progress dashboard summary as returned by the API.

    Mirrors app.services.progress.ProgressStats field-for-field - this
    schema exists separately (rather than reusing the dataclass
    directly as response_model) purely so FastAPI generates OpenAPI
    docs for it, same reasoning as every other *Out schema in this app.
    """

    total_documents: int
    total_flashcards: int
    flashcards_due_now: int
    cards_mastered: int
    reviews_today: int
    reviews_last_7_days: int
    accuracy_last_7_days: Optional[float]
    current_streak_days: int
