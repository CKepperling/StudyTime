from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.progress import ProgressOut
from app.services.progress import compute_progress_stats

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The current user's study progress dashboard summary.

    All the actual aggregation lives in services/progress.py - this
    endpoint is just wiring auth and the DB session to it, same
    division of labor as api/flashcards.py's review endpoint delegates
    the SM-2 math to services/sm2.py.
    """
    stats = compute_progress_stats(db, current_user.id)
    return ProgressOut(**stats.__dict__)
