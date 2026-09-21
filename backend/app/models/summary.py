import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.document import Document


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)

    # "documents" (plural) to match Document.__tablename__ exactly.
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    # Enum(DifficultyLevel) wraps the column so the DB enforces valid values too.
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(Enum(DifficultyLevel))

    content: Mapped[str] = mapped_column(String)

    # default=datetime.utcnow means you never have to pass this manually —
    # it's filled in automatically whenever a row is created.
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="summaries")