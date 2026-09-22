from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Shape of a document as returned by the API.

    No storage_path here, same reasoning as UserOut leaving out
    hashed_password - storage_path is where the file sits on OUR
    disk, not something the outside world needs or should be able
    to guess at.
    """

    id: int
    filename: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
