import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentOut
from app.storage import UPLOAD_DIR
from app.workers.tasks import extract_document_text

router = APIRouter(prefix="/documents", tags=["documents"])

# Generous enough for lecture-slide PDFs; just a backstop against
# someone filling the disk with one absurd upload. The extraction
# worker may end up wanting its own, separate limit for how much text
# it's willing to process.
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

    # Hand off to the Celery worker rather than extracting text inline
    # here - a multi-page PDF can take real time to process, and this
    # request shouldn't make the person wait on it just to get back
    # "yes, I received your file."
    extract_document_text.delay(document.id)

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
