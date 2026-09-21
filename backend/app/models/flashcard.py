import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.review_log import ReviewLog


class FlashcardSource(str, enum.Enum):
    AI_GENERATED = "ai_generated"
    MANUAL = "manual"


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    front: Mapped[str] = mapped_column(String)
    back: Mapped[str] = mapped_column(String)

    source: Mapped[FlashcardSource] = mapped_column(Enum(FlashcardSource))

    # --- SM-2 scheduling state, added proactively for T16/T17 ---
    # ease_factor starts at 2.5 per the standard SM-2 algorithm's default.
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    # interval_days: how many days until the NEXT review after the last one.
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    # repetitions: consecutive correct reviews in a row (resets on a bad grade).
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    # due_at defaults to "now" so a brand-new card shows up as due immediately.
    due_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="flashcards")
    review_logs: Mapped[list["ReviewLog"]] = relationship(back_populates="flashcard")