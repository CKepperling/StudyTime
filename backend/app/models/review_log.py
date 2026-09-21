from datetime import datetime

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id"))

    # grade is a plain int (0-3) matching the four review buttons:
    # 0=Again, 1=Hard, 2=Good, 3=Easy. The actual SM-2 math that turns
    # this into a new ease_factor/interval happens in T16, not here —
    # this table just records what the user picked and when.
    grade: Mapped[int] = mapped_column(Integer)

    reviewed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    flashcard: Mapped["Flashcard"] = relationship(back_populates="review_logs")