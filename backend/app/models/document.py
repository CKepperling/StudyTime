from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# See user.py for why these are guarded by TYPE_CHECKING instead of
# being normal imports - this file references all four by name.
if TYPE_CHECKING:
    from app.models.flashcard import Flashcard
    from app.models.note import Note
    from app.models.practice_test import PracticeTest
    from app.models.summary import Summary
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    # ForeignKey("users.id") points at the TABLE name + column, not the class.
    # This is what actually links a document to its owner in the database.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # filename is the ORIGINAL name the user uploaded with (what the UI
    # shows them) - it's just for display, and two documents can share
    # one. storage_path is the actual name it's saved under on disk
    # (a UUID + ".pdf"), so uploads never collide or overwrite each
    # other and a filename can't be crafted to read someone else's file.
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(255))

    # status tracks upload -> extraction -> AI generation progress.
    # Plain string for now; could become an Enum later like difficulty_level.
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Optional[str] (not str | None) - the | union syntax needs Python 3.10+.
    # ruff.toml pins target-version to py39 so ruff stops suggesting X | Y here.
    extracted_text: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # The other half of the relationship declared on User.
    # back_populates="documents" must match the attribute name on User exactly.
    user: Mapped["User"] = relationship(back_populates="documents")

    # Every one of these mirrors a relationship declared on the OTHER model,
    # pointing back here. back_populates on each side must name the attribute
    # on the opposite class exactly, or SQLAlchemy errors at app startup.
    summaries: Mapped[list["Summary"]] = relationship(back_populates="document")
    flashcards: Mapped[list["Flashcard"]] = relationship(back_populates="document")
    notes: Mapped[list["Note"]] = relationship(back_populates="document")
    practice_tests: Mapped[list["PracticeTest"]] = relationship(back_populates="document")