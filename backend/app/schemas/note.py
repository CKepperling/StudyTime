from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NoteCreate(BaseModel):
    """Shape of a POST /documents/{document_id}/notes request body."""
    content: str


class NoteUpdate(BaseModel):
    """Shape of a PUT /notes/{note_id} request body."""
    content: str


class NoteOut(BaseModel):
    """Shape of a note as returned by the API."""
    id: int
    document_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)