import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

# Where uploaded PDFs actually live on disk. Configurable via env var
# (a real deployment would point this at a mounted volume or object
# storage) but defaults to a local "uploads" folder for dev/CI, same
# spirit as DATABASE_URL falling back to nothing without one set.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Generous enough for lecture-slide PDFs; just a backstop against
# someone filling the disk with one absurd upload. T18 (PDF text
# extraction) may end up wanting its own, separate limit.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported right now",
        )

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large (max 20MB)",
        )

    # A random name on disk - not the user's original filename - so two
    # people uploading "notes.pdf" never collide, and nobody can request
    # another user's file just by guessing its display name.
    storage_path = f"{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / storage_path).write_bytes(contents)

    document = Document(
        user_id=current_user.id,
        filename=file.filename or storage_path,
        storage_path=storage_path,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every document the CURRENT user uploaded - never another user's.

    Filtering by current_user.id here (rather than trusting a query
    param) is what stops one logged-in user from listing or paging
    through everyone else's uploads.
    """
    documents = (
        db.execute(
            select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(Document.created_at.desc())
        )
        .scalars()
        .all()
    )
    return documents
