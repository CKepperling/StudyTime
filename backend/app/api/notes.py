from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.document import Document
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(tags=["notes"])


def _get_owned_document(document_id: int, current_user: User, db: Session) -> Document:
    """Fetch a document, but only if the current user actually owns it.

    404 (not 403) whether the document doesn't exist at all, or exists
    but belongs to someone else - same reasoning as login's identical
    error for "wrong password" vs "no such user": a 403 here would
    confirm to an attacker that a given document_id is real, just not
    theirs, which is information they shouldn't get for free.
    """
    document = db.get(Document, document_id)
    if document is None or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def _get_owned_note(note_id: int, current_user: User, db: Session) -> Note:
    """Fetch a note, but only if the current user owns its PARENT document.

    Note has no user_id of its own - ownership only exists one level up,
    through document_id - so this joins through Document to check it,
    same 404-not-403 reasoning as _get_owned_document above.
    """
    note = db.get(Note, note_id)
    if note is None or note.document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


@router.get("/documents/{document_id}/notes", response_model=list[NoteOut])
def list_notes(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Confirms the document is the current user's BEFORE listing its
    # notes - without this check, any logged-in user could read any
    # document's notes just by guessing a document_id in the URL.
    _get_owned_document(document_id, current_user, db)

    notes = (
        db.execute(
            select(Note)
            .where(Note.document_id == document_id)
            .order_by(Note.created_at.desc())
        )
        .scalars()
        .all()
    )
    return notes


@router.post(
    "/documents/{document_id}/notes",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    document_id: int,
    note_in: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_document(document_id, current_user, db)

    note = Note(document_id=document_id, content=note_in.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.put("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    note_in: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(note_id, current_user, db)

    note.content = note_in.content
    db.commit()
    db.refresh(note)  # picks up updated_at's onupdate=datetime.utcnow
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(note_id, current_user, db)

    db.delete(note)
    db.commit()