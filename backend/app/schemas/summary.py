from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.summary import DifficultyLevel


class SummaryOut(BaseModel):
    """Shape of a summary as returned by the API."""

    id: int
    document_id: int
    difficulty_level: DifficultyLevel
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)